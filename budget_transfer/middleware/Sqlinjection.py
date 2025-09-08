# Create a file: user_management/middleware.py or create a new file like security/middleware.py

import re
import logging
import json
from django.http import HttpResponseBadRequest
from django.http.request import RawPostDataException
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    Middleware to detect and block potential SQL injection attempts
    """

    # Common SQL injection patterns - More specific to reduce false positives
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')\s*(union|select|insert|delete|update|drop|create|exec)",  # Quotes followed by SQL keywords
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%23)|(#))",  # Equals with quotes/comments
        r"((\%27)|(\')|(\-\-)|(\%23)|(#))\s*(union|select|insert|delete|update|drop)",  # Comments/quotes with SQL
        r"union\s+(all\s+)?select",  # UNION SELECT
        r"select\s+.*\s+from\s+",  # SELECT FROM
        r"insert\s+into\s+",  # INSERT INTO
        r"delete\s+from\s+",  # DELETE FROM
        r"update\s+.*\s+set\s+",  # UPDATE SET
        r"drop\s+(table|database|schema)",  # DROP statements
        r"create\s+(table|database|schema)",  # CREATE statements
        r"exec\s*\(",  # EXEC commands
        r"<\s*script[^>]*>",  # Script tags
        r"javascript\s*:",  # JavaScript
        r"vbscript\s*:",  # VBScript
        r"on(load|error|click|mouse|focus|blur)\s*=",  # Event handlers
        r"'\s*(or|and)\s+('|\d+\s*=\s*\d+|true|false)",  # OR/AND injection patterns
        r"'\s*=\s*'\s*(or|and)",  # Equality with OR/AND
        r";\s*(drop|delete|insert|update|create|exec)",  # Semicolon attacks
        r"\/\*.*\*\/",  # SQL comments
        r"--\s*[^\r\n]*",  # SQL line comments
        r"(concat|char|ascii|substring|length|version|database|user|current_user)\s*\(",  # SQL functions
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SQL_INJECTION_PATTERNS
        ]

        # Whitelist patterns for legitimate content
        self.whitelist_patterns = [
            r"^/api/(approvals|budget|auth|accounts-entities|admin_panel|adjd-transfers)/",  # API endpoints
            r"workflow",  # Allow "workflow" in content
            r"approval",  # Allow "approval" in content
            r"transfer",  # Allow "transfer" in content
            r"stage",  # Allow "stage" in content
        ]
        self.compiled_whitelist = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.whitelist_patterns
        ]

    def __call__(self, request):
        # Skip SQL injection check for approval API endpoints
        if request.path.startswith("/api/approvals/"):
            # For approval endpoints, only check for very obvious SQL injection attempts
            if self.contains_obvious_sql_injection(request):
                logger.warning(
                    f"Obvious SQL injection attempt detected from {request.META.get('REMOTE_ADDR')}: {request.get_full_path()}"
                )
                return HttpResponseBadRequest("Invalid request detected")
        else:
            # Check request before processing for other endpoints
            if self.contains_sql_injection(request):
                logger.warning(
                    f"SQL injection attempt detected from {request.META.get('REMOTE_ADDR')}: {request.get_full_path()}"
                )
                return HttpResponseBadRequest("Invalid request detected")

        response = self.get_response(request)
        return response

    def contains_sql_injection(self, request):
        """
        Check if request contains potential SQL injection
        """
        # Normalize content type (ignore charset, etc.)
        content_type = (request.content_type or "").split(";")[0].lower()

        # Check GET parameters
        for key, value in request.GET.items():
            if self.is_malicious(value, request.path):
                logger.warning(f"SQL injection in GET parameter '{key}': {value}")
                return True

        # Only inspect one source based on content type to avoid consuming the stream twice
        try:
            if content_type == "application/json":
                # Safely inspect JSON body without touching request.POST
                try:
                    body_bytes = (
                        request.body
                    )  # May raise RawPostDataException if already consumed
                    json_data = json.loads(body_bytes.decode("utf-8"))
                    if self.check_json_data(json_data, request.path):
                        return True
                except RawPostDataException:
                    # Body already consumed (e.g., by previous middleware) — skip JSON inspection
                    logger.debug(
                        "Skipping JSON body inspection: raw post data already consumed"
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If we can't parse JSON, check the raw body (best-effort)
                    try:
                        raw = body_bytes.decode("utf-8", errors="ignore")
                        if self.is_malicious(raw, request.path):
                            logger.warning(f"SQL injection in request body: {raw}")
                            return True
                    except Exception:
                        pass

            elif content_type.startswith("multipart/"):
                # File uploads: never touch request.body; only inspect form fields
                for key, value in request.POST.items():
                    if self.is_malicious(value, request.path):
                        logger.warning(
                            f"SQL injection in multipart POST parameter '{key}': {value}"
                        )
                        return True

            elif content_type in ("application/x-www-form-urlencoded", "text/plain"):
                # Regular forms: POST is safe to read; avoid body access
                for key, value in request.POST.items():
                    if self.is_malicious(value, request.path):
                        logger.warning(
                            f"SQL injection in POST parameter '{key}': {value}"
                        )
                        return True
            else:
                # Fallback: attempt to read body if available and not consumed
                try:
                    raw = request.body.decode("utf-8", errors="ignore")
                    if raw and self.is_malicious(raw, request.path):
                        logger.warning(f"SQL injection in raw request body: {raw}")
                        return True
                except RawPostDataException:
                    logger.debug(
                        "Skipping raw body inspection: raw post data already consumed"
                    )
        except Exception:
            # Be conservative; do not block the request on middleware inspection errors
            logger.debug(
                "SQL injection inspection encountered a non-fatal error", exc_info=True
            )

        # Check path (be more lenient with paths)
        if self.is_malicious_path(request.path):
            logger.warning(f"SQL injection in request path: {request.path}")
            return True

        return False

    def check_json_data(self, data, context_path=None):
        """
        Recursively check JSON data for SQL injection patterns
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if self.is_malicious(str(key), context_path) or self.check_json_data(
                    value, context_path
                ):
                    logger.warning(
                        f"SQL injection in JSON key '{key}' or value: {value}"
                    )
                    return True
        elif isinstance(data, list):
            for item in data:
                if self.check_json_data(item, context_path):
                    return True
        elif isinstance(data, str):
            if self.is_malicious(data, context_path):
                logger.warning(f"SQL injection in JSON string: {data}")
                return True
        return False

    def is_malicious_path(self, path):
        """
        Check if path contains SQL injection patterns (more restrictive for paths)
        """
        dangerous_path_patterns = [
            r"union(.*?)select",
            r"drop(.*?)table",
            r"exec(.*?)\s",
            r"delete(.*?)from",
            r"insert(.*?)into",
        ]

        for pattern_str in dangerous_path_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(path):
                return True
        return False

    def is_malicious(self, value, context_path=None):
        """
        Check if a value contains SQL injection patterns
        """
        if not isinstance(value, str):
            value = str(value)

        # Check if this is from a whitelisted API endpoint
        if context_path:
            for whitelist_pattern in self.compiled_whitelist:
                if whitelist_pattern.search(context_path):
                    # For whitelisted endpoints, only check for very obvious SQL injection
                    obvious_sql_patterns = [
                        r"union\s+(all\s+)?select",
                        r"drop\s+(table|database)",
                        r"insert\s+into\s+",
                        r"delete\s+from\s+",
                        r"'\s*(or|and)\s+('|\d+\s*=\s*\d+)",
                    ]
                    for pattern_str in obvious_sql_patterns:
                        pattern = re.compile(pattern_str, re.IGNORECASE)
                        if pattern.search(value):
                            return True
                    return False

        # Standard check for all patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                return True
        return False

    def contains_obvious_sql_injection(self, request):
        """
        Check for only very obvious SQL injection attempts (for API endpoints)
        """
        # Only check for the most obvious SQL injection patterns
        obvious_patterns = [
            r"union\s+(all\s+)?select",  # UNION SELECT
            r"drop\s+(table|database|schema)",  # DROP statements
            r"insert\s+into\s+.*values",  # INSERT statements
            r"delete\s+from\s+\w+",  # DELETE statements
            r"'\s*(or|and)\s+('1'='1'|'1'='1|1=1)",  # Classic injection
            r";\s*(drop|delete|insert|update|create)\s+",  # Semicolon attacks
            r"exec\s*\(",  # EXEC commands
            r"<\s*script[^>]*>",  # Script tags
        ]

        compiled_obvious = [
            re.compile(pattern, re.IGNORECASE) for pattern in obvious_patterns
        ]

        # Check GET parameters
        for key, value in request.GET.items():
            for pattern in compiled_obvious:
                if pattern.search(str(value)):
                    logger.warning(
                        f"Obvious SQL injection in GET parameter '{key}': {value}"
                    )
                    return True

        # Check JSON body for API endpoints
        content_type = (request.content_type or "").split(";")[0].lower()
        if content_type == "application/json":
            try:
                body_bytes = request.body
                json_data = json.loads(body_bytes.decode("utf-8"))
                return self.check_obvious_json_data(json_data, compiled_obvious)
            except (json.JSONDecodeError, UnicodeDecodeError, RawPostDataException):
                pass

        return False

    def check_obvious_json_data(self, data, compiled_patterns):
        """
        Check JSON data for only obvious SQL injection patterns
        """
        if isinstance(data, dict):
            for key, value in data.items():
                for pattern in compiled_patterns:
                    if pattern.search(str(key)) or pattern.search(str(value)):
                        logger.warning(f"Obvious SQL injection in JSON: {key}={value}")
                        return True
                if isinstance(value, (dict, list)):
                    if self.check_obvious_json_data(value, compiled_patterns):
                        return True
        elif isinstance(data, list):
            for item in data:
                if self.check_obvious_json_data(item, compiled_patterns):
                    return True
        elif isinstance(data, str):
            for pattern in compiled_patterns:
                if pattern.search(data):
                    logger.warning(f"Obvious SQL injection in JSON string: {data}")
                    return True
        return False
