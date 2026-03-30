"""
Custom OpenAPI schema generator for FastAPI.
Generates code samples, logos, and tag groups for the OpenAPI schema.
"""

import json
from fastapi.openapi.utils import get_openapi
from typing import Any, Dict, List, Optional, Tuple


class OpenAPICodeSampleGenerator:
    """
    Generates code samples for OpenAPI operations in multiple languages.

    Supports:
    - cURL
    - Python (requests library)
    - JavaScript (fetch API)
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.nl = "\n"
        self.indent = "    "

    def extract_headers_and_payload(
        self, operation: Dict[str, Any], components: Dict[str, Any]
    ) -> Tuple[Dict[str, str], Dict[str, Any], str]:
        """
        Extract headers, payload example, and content type from an OpenAPI operation.

        Args:
            operation: The OpenAPI operation object
            components: The components section of the OpenAPI schema

        Returns:
            Tuple of (headers dict, payload example dict, content type string)
        """
        headers = self._extract_headers(operation)
        payload_example, content_type = self._extract_payload(
            operation, components, headers
        )

        return headers, payload_example, content_type

    def _extract_headers(self, operation: Dict[str, Any]) -> Dict[str, str]:
        """Extract header parameters from the operation."""
        headers = {}

        for param in operation.get("parameters", []):
            if param.get("in") != "header":
                continue

            param_name = param["name"]
            param_schema = param.get("schema", {})

            # Handle Authorization header specially
            if param_name == "Authorization":
                headers[param_name] = "Bearer <token>"
            # Handle anyOf schemas
            elif "anyOf" in param_schema:
                types = [v.get("type", "string") for v in param_schema["anyOf"]]
                headers[param_name] = " | ".join(types)
            # Standard type
            else:
                headers[param_name] = param_schema.get("type", "string")

        return headers

    def _extract_payload(
        self,
        operation: Dict[str, Any],
        components: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], str]:
        """Extract payload example and content type from request body."""
        payload_example = {}
        content_type = ""

        request_body = operation.get("requestBody", {}).get("content", {})

        # Prioritize JSON, then form-urlencoded
        content_types_priority = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]

        for ct in content_types_priority:
            if ct in request_body:
                content_type = ct
                headers["Content-Type"] = ct
                break

        if not content_type and request_body:
            # Fall back to first available content type
            content_type = next(iter(request_body.keys()))
            headers["Content-Type"] = content_type

        if content_type in request_body:
            content = request_body[content_type]
            payload_example = self._build_payload_example(
                content.get("schema", {}), components
            )

        return payload_example, content_type

    def _build_payload_example(
        self, schema: Dict[str, Any], components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a payload example from a schema definition."""
        payload = {}

        # Handle $ref
        if "$ref" in schema:
            schema_name = schema["$ref"].split("/")[-1]
            schema = components.get("schemas", {}).get(schema_name, {})

        properties = schema.get("properties", {})

        for key, value in properties.items():
            # Handle anyOf schemas
            if "anyOf" in value:
                types = []
                for variant in value["anyOf"]:
                    if "type" in variant:
                        types.append(variant["type"])
                    elif "$ref" in variant:
                        ref_name = variant["$ref"].split("/")[-1]
                        ref_type = (
                            components.get("schemas", {})
                            .get(ref_name, {})
                            .get("type", "object")
                        )
                        types.append(ref_type)
                payload[key] = " | ".join(types) if types else "string"

            # Handle $ref in property
            elif "$ref" in value:
                ref_name = value["$ref"].split("/")[-1]
                payload[key] = f"<{ref_name}>"

            # Handle arrays
            elif value.get("type") == "array":
                item_type = value.get("items", {}).get("type", "string")
                payload[key] = f"array[{item_type}]"

            # Standard types
            else:
                # Provide example values for common types
                type_examples = {
                    "string": "<string>",
                    "integer": 0,
                    "number": 0.0,
                    "boolean": True,
                    "object": {},
                }
                payload[key] = type_examples.get(
                    value.get("type", "string"), value.get("type", "string")
                )

        return payload

    def _build_query_string(self, operation: Dict[str, Any]) -> str:
        """Build query string from query parameters."""
        query_params = [
            param
            for param in operation.get("parameters", [])
            if param.get("in") == "query"
        ]

        if not query_params:
            return ""

        query_parts = []
        for param in query_params:
            param_name = param["name"]
            # Show type hint in the placeholder
            param_type = param.get("schema", {}).get("type", "string")
            query_parts.append(f"{param_name}=<{param_type}>")

        return f"?{('&'.join(query_parts))}"

    def generate_curl_sample(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        query_string: str,
    ) -> str:
        """Generate cURL command sample."""
        url = f"{self.base_url}{path}{query_string}"

        header_lines = "".join(
            f"{self.indent}-H '{k}: {v}' \\\n" for k, v in headers.items()
        )

        payload_line = ""
        if payload:
            payload_json = json.dumps(payload, indent=2)
            payload_line = f"{self.indent}-d '{payload_json}' \\\n"

        curl_command = (
            f"curl -X {method.upper()} '{url}' \\\n" f"{header_lines}" f"{payload_line}"
        ).rstrip(" \\\n")

        return curl_command

    def generate_python_sample(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        query_string: str,
        content_type: str,
    ) -> str:
        """Generate Python (requests) sample."""
        url = f"{self.base_url}{path}{query_string}"

        # Determine whether to use json= or data= parameter
        is_form_data = "form-urlencoded" in content_type or "multipart" in content_type

        code = f"import requests{self.nl}"

        if not is_form_data:
            code += f"import json{self.nl}"

        code += f"{self.nl}"
        code += f'url = "{url}"{self.nl}'
        code += f"headers = {json.dumps(headers, indent=4)}{self.nl}"

        if payload:
            code += f"payload = {json.dumps(payload, indent=4)}{self.nl}"

        code += f"{self.nl}"

        # Build the request call
        request_params = ["url", "headers=headers"]
        if payload:
            if is_form_data:
                request_params.append("data=payload")
            else:
                request_params.append("json=payload")

        code += f"response = requests.{method.lower()}({', '.join(request_params)}){self.nl}"
        code += f"print(response.json())"

        return code

    def generate_javascript_sample(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        query_string: str,
        content_type: str,
    ) -> str:
        """Generate JavaScript (fetch) sample."""
        url = f"{self.base_url}{path}{query_string}"

        is_form_data = "form-urlencoded" in content_type

        code = f'const url = "{url}";{self.nl}'
        code += f"const headers = {json.dumps(headers, indent=4)};{self.nl}"

        if payload:
            if is_form_data:
                code += f"const formData = new URLSearchParams();{self.nl}"
                for key, value in payload.items():
                    code += f'formData.append("{key}", {json.dumps(value)});{self.nl}'
                code += f"{self.nl}"
            else:
                code += f"const payload = {json.dumps(payload, indent=4)};{self.nl}"
                code += f"{self.nl}"

        # Build fetch options
        fetch_options = [f"method: '{method.upper()}'", "headers: headers"]

        if payload:
            if is_form_data:
                fetch_options.append("body: formData")
            else:
                fetch_options.append("body: JSON.stringify(payload)")

        code += f"fetch(url, {{{', '.join(fetch_options)}}}){self.nl}"
        code += f"{self.indent}.then(response => response.json()){self.nl}"
        code += f"{self.indent}.then(data => console.log(data)){self.nl}"
        code += f"{self.indent}.catch(error => console.error('Error:', error));"

        return code

    def generate_all_samples(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        components: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Generate code samples for all supported languages.

        Returns:
            List of code sample dictionaries with 'lang', 'source', and 'label' keys
        """
        headers, payload, content_type = self.extract_headers_and_payload(
            operation, components
        )
        query_string = self._build_query_string(operation)

        samples = [
            {
                "lang": "curl",
                "source": self.generate_curl_sample(
                    path, method, headers, payload, query_string
                ),
                "label": "cURL",
            },
            {
                "lang": "python",
                "source": self.generate_python_sample(
                    path, method, headers, payload, query_string, content_type
                ),
                "label": "Python",
            },
            {
                "lang": "javascript",
                "source": self.generate_javascript_sample(
                    path, method, headers, payload, query_string, content_type
                ),
                "label": "JavaScript",
            },
        ]

        return samples


class EnhancedOpenAPIGenerator:
    """
    Enhanced OpenAPI schema generator with custom branding and organization.
    """

    def __init__(
        self,
        app,
        project_name: str,
        version: str,
        base_url: str,
        support_email: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags_metadata: Optional[List[Dict[str, Any]]] = None,
        logo_url: Optional[str] = None,
        tag_groups: Optional[List[Dict[str, Any]]] = None,
    ):
        self.app = app
        self.project_name = project_name
        self.version = version
        self.base_url = base_url
        self.support_email = support_email
        self.summary = summary
        self.description = description
        self.tags_metadata = tags_metadata or []
        self.logo_url = (
            logo_url or "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        )
        self.tag_groups = tag_groups or []
        self.code_generator = OpenAPICodeSampleGenerator(base_url)

    def generate_schema(self) -> Dict[str, Any]:
        """
        Generate the complete OpenAPI schema with all enhancements.

        Returns:
            Complete OpenAPI schema dictionary
        """
        # Check if schema already exists
        if self.app.openapi_schema:
            return self.app.openapi_schema

        # Generate base schema
        openapi_schema = get_openapi(
            title=self.project_name,
            version=self.version,
            summary=self.summary,
            description=self.description,
            tags=self.tags_metadata,
            routes=self.app.routes,
        )

        # Add custom branding
        self._add_branding(openapi_schema)

        # Add tag groups for better organization
        if self.tag_groups:
            openapi_schema["x-tagGroups"] = self.tag_groups

        # Generate code samples for all endpoints
        self._add_code_samples(openapi_schema)

        # Add security schemes if not present
        self._enhance_security_schemes(openapi_schema)

        # Cache and return
        self.app.openapi_schema = openapi_schema
        return openapi_schema

    def _add_branding(self, schema: Dict[str, Any]) -> None:
        """Add logo and custom branding to the schema."""
        if "info" not in schema:
            schema["info"] = {}

        schema["info"]["x-logo"] = {
            "url": self.logo_url,
            "altText": f"{self.project_name} Logo",
        }

        # Add contact and license if needed
        if "contact" not in schema["info"]:
            schema["info"]["contact"] = {
                "name": "API Support",
                "email": self.support_email,
            }

    def _add_code_samples(self, schema: Dict[str, Any]) -> None:
        """Add code samples to all operations."""
        components = schema.get("components", {})

        for path, path_item in schema.get("paths", {}).items():
            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                if method not in path_item:
                    continue

                operation = path_item[method]

                try:
                    samples = self.code_generator.generate_all_samples(
                        path, method, operation, components
                    )
                    operation["x-code-samples"] = samples
                except Exception as e:
                    print(
                        f"Warning: Failed to generate code samples for {method.upper()} {path}: {e}"
                    )

    def _enhance_security_schemes(self, schema: Dict[str, Any]) -> None:
        """Add or enhance security schemes."""
        if "components" not in schema:
            schema["components"] = {}

        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}

        security_schemes = schema["components"]["securitySchemes"]


def create_custom_openapi_generator(
    app,
    env_config,
    docs_summary: Optional[str] = None,
    docs_description: Optional[str] = None,
    docs_tags_metadata: Optional[List[Dict[str, Any]]] = None,
    logo_url: Optional[str] = None,
    custom_tag_groups: Optional[List[Dict[str, Any]]] = None,
):
    """
    Factory function to create and attach custom OpenAPI generator to FastAPI app.

    Args:
        app: FastAPI application instance
        env_config: Configuration object with BASE_URL, PROJECT_NAME, INSTANCE
        docs_summary: Optional API summary
        docs_description: Optional API description
        docs_tags_metadata: Optional list of tag metadata
        logo_url: Optional custom logo URL
        custom_tag_groups: Optional custom tag groups

    Returns:
        Function that generates OpenAPI schema
    """
    generator = EnhancedOpenAPIGenerator(
        app=app,
        project_name=env_config.app_name,
        version=env_config.app_version,
        base_url=env_config.base_url,
        support_email=env_config.support_email,
        summary=docs_summary,
        description=docs_description,
        tags_metadata=docs_tags_metadata,
        logo_url=logo_url,
        tag_groups=custom_tag_groups,
    )

    return generator.generate_schema
