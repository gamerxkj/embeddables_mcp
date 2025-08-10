#!/usr/bin/env python3

"""
servicenow_mcp_server.py - ServiceNow Embedding Diagnostics MCP Server (Remote/Local Compatible)
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers
from starlette.requests import Request
from starlette.responses import JSONResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("servicenow-mcp")

# Initialization state
server_initialized = False

def mark_server_initialized():
    global server_initialized
    server_initialized = True
    logger.info("Server marked as initialized")

class ServiceNowSession:
    def __init__(self):
        self.initialized = False

    def mark_initialized(self):
        self.initialized = True
        logger.info("ServiceNowSession marked as initialized")

    def _get_credentials(self, context=None, username=None, password=None):
        headers = get_http_headers()
        return (
            username or headers.get("username"),
            password or headers.get("password"),
        )

    def connect(self, instance_url: str, username: str = None, password: str = None, context: Context = None) -> Dict[str, Any]:
        global server_initialized
        if not server_initialized:
            logger.warning("Server not yet initialized, marking now")
            mark_server_initialized()

        if not self.initialized:
            self.mark_initialized()

        username, password = self._get_credentials(context, username, password)
        if instance_url.endswith('/'):
            instance_url = instance_url[:-1]
        if not instance_url.startswith('http'):
            instance_url = f"https://{instance_url}"

        logger.info(f"Connecting to: {instance_url}")
        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        try:
            test_url = f"{instance_url}/api/now/table/sys_properties?sysparm_limit=1"
            response = session.get(test_url)
            logger.info(f"Status: {response.status_code} | Text: {response.text[:300]}")
            if response.status_code == 200:
                return {"success": True, "message": "Connected"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_embeddables_enabled(self, instance_url: str, username=None, password=None):
        username, password = self._get_credentials(username=username, password=password)
        connect_result = self.connect(instance_url, username, password)
        if not connect_result.get("success"):
            return connect_result

        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        url = f"{instance_url}/api/now/table/sys_properties"
        params = {'sysparm_query': 'name=glide.uxf.lib.embeddables.enabled', 'sysparm_fields': 'name,value'}

        try:
            response = session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                enabled = data.get("result", [{}])[0].get("value") == "true"
                return {"success": True, "enabled": enabled}
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_embeddables_plugin(self, instance_url: str, username=None, password=None):
        return self._check_plugin_status(instance_url, username, password, "com.glide.ux.embeddables")


    def check_client_access_plugin(self, instance_url: str, username=None, password=None):
        return self._check_plugin_status(instance_url, username, password, "com.glide.security.client_access")

    def _check_plugin_status(self, instance_url: str, username=None, password=None, plugin_id: str = None):
        username, password = self._get_credentials(username=username, password=password)
        connect_result = self.connect(instance_url, username, password)
        if not connect_result.get("success"):
            return connect_result

        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        url = f"{instance_url}/api/now/table/v_plugin"
        params = {
            "sysparm_query": f"id={plugin_id}",
            "sysparm_fields": "id,active,name"
        }

        try:
            response = session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", [{}])[0]
                active = result.get("active") == "active"
                return {"success": True, "active": active}
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_cors_rule(self, instance_url: str, username=None, password=None, domain=None):
        from urllib.parse import urlparse
        username, password = self._get_credentials(username=username, password=password)
        connect_result = self.connect(instance_url, username, password)
        if not connect_result.get("success"):
            return connect_result

        # Format domain for query
        if domain:
            # If domain doesn't start with http/https, we need to try with protocols
            if not domain.startswith("http"):
                # Remove any accidental trailing slashes
                if domain.endswith('/'):
                    domain = domain[:-1]
                
                # Create query to match both with and without protocol
                domain_query = f'domain=https://{domain}^ORdomain=http://{domain}^ORdomain={domain}'
            else:
                # Domain already has protocol, use as is
                domain_query = f'domain={domain}'
        else:
            # No domain provided, get all rules
            domain_query = ''

        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        url = f"{instance_url}/api/now/table/sys_cors_rule"
        params = {'sysparm_query': domain_query, 'sysparm_fields': 'domain,active'}

        try:
            response = session.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("result", [])
                active = any(rule.get("active") == "true" for rule in data)
                return {"success": True, "exists": bool(data), "active": active}
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_all_embeddable_activated(self, instance_url: str, username=None, password=None):
        """Check for all records in 'sys_ux_embeddable_macroponent' table and their activation status."""
        username, password = self._get_credentials(username=username, password=password)
        connect_result = self.connect(instance_url, username, password)
        if not connect_result.get("success"):
            return connect_result

        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        url = f"{instance_url}/api/now/table/sys_ux_embeddable_macroponent"
        params = {'sysparm_fields': 'tag_name,active,sys_id'}

        try:
            response = session.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("result", [])
                embeddables = []
                for item in data:
                    embeddables.append({
                        "name": item.get("tag_name"),
                        "active": item.get("active") == "true",
                        "sys_id": item.get("sys_id")
                    })
                return {
                    "success": True, 
                    "total_count": len(embeddables),
                    "active_count": sum(1 for e in embeddables if e["active"]),
                    "embeddables": embeddables
                }
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def check_embeddable_activated(self, instance_url: str, macroponent_name: str, username=None, password=None):
        """Check for a specific macroponent by name and its activation status."""
        username, password = self._get_credentials(username=username, password=password)
        connect_result = self.connect(instance_url, username, password)
        if not connect_result.get("success"):
            return connect_result

        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        url = f"{instance_url}/api/now/table/sys_ux_embeddable_macroponent"
        query = f"macroponent.nameSTARTSWITH{macroponent_name}"
        params = {'sysparm_query': query, 'sysparm_fields': 'tag_name,active,sys_id'}

        try:
            response = session.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("result", [])
                embeddables = []
                for item in data:
                    embeddables.append({
                        "name": item.get("tag_name"),
                        "internal_name": item.get("name"),
                        "active": item.get("active") == "true",
                        "sys_id": item.get("sys_id")
                    })
                return {
                    "success": True, 
                    "found": len(embeddables) > 0,
                    "count": len(embeddables),
                    "all_active": all(e["active"] for e in embeddables) if embeddables else False,
                    "embeddables": embeddables
                }
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_all_checks(self, instance_url: str, username: str = None, password: str = None, domain: str = None):
        """Runs all checks and returns a report."""
        username, password = self._get_credentials(username=username, password=password)
        if not self.initialized:
            self.connect(instance_url, username, password)

        report = {}
        report['embeddables_enabled'] = self.check_embeddables_enabled(instance_url, username, password)
        report['embeddables_plugin'] = self.check_embeddables_plugin(instance_url, username, password)
        report['client_access_plugin'] = self.check_client_access_plugin(instance_url, username, password)
        report['cors_rule'] = self.check_cors_rule(instance_url, username, password, domain)
        report['embeddable_activation'] = self.check_all_embeddable_activated(instance_url, username, password)

        return report

# Create global instances
sn_session = ServiceNowSession()
mcp = FastMCP(name="ServiceNow Embedding Diagnostics", instructions="Run SN diagnostics")

@mcp.tool()
def connect_to_instance(instance_url: str, username: str = "", password: str = "", context: Context = None):
    return sn_session.connect(instance_url, username, password, context)

@mcp.tool()
def check_embeddables_enabled(instance_url: str, username: str = "", password: str = ""):
    return sn_session.check_embeddables_enabled(instance_url, username, password)

@mcp.tool()
def check_embeddables_plugin(instance_url: str, username: str = "", password: str = ""):
    return sn_session._check_plugin_status(instance_url, username, password, "com.glide.ux.embeddables")

@mcp.tool()
def check_client_access_plugin(instance_url: str, username: str = "", password: str = ""):
    return sn_session.check_plugin_status(instance_url, username, password, "com.glide.security.client_access")

@mcp.tool()
def check_cors_rule(instance_url: str, username: str = "", password: str = "", domain: str = ""):
    return sn_session.check_cors_rule(instance_url, username, password, domain)

@mcp.tool()
def check_all_embeddable_activated(instance_url: str, username: str = "", password: str = ""):
    """Check for all records in 'sys_ux_embeddable_macroponent' table and their activation status."""
    return sn_session.check_all_embeddable_activated(instance_url, username, password)

@mcp.tool()
def check_embeddable_activated(instance_url: str, macroponent_name: str, username: str = "", password: str = ""):
    """Check for a specific macroponent by name and its activation status."""
    return sn_session.check_embeddable_activated(instance_url, macroponent_name, username, password)

@mcp.tool()
def run_all_checks(instance_url: str, username: str = "", password: str = "", domain: str = ""):
    """Runs all checks and returns a report."""
    return sn_session.run_all_checks(instance_url, username, password, domain)

# ---------------------- Startup and Server ----------------------

if __name__ == "__main__":
    import uvicorn

    app = mcp.sse_app()

    # Handle OAuth discovery probes gracefully (204 No Content)
    @app.route("/.well-known/oauth-authorization-server", methods=["GET", "OPTIONS"])
    @app.route("/.well-known/oauth-protected-resource", methods=["GET", "OPTIONS"])
    async def noop_oauth(request: Request):
        return JSONResponse(status_code=204, content={})

    # Block incoming requests if not initialized
    @app.middleware("http")
    async def block_if_uninitialized(request: Request, call_next):
        if not server_initialized:
            logger.warning("Received request before initialization was complete")
            return JSONResponse(status_code=503, content={"error": "Server not yet ready"})
        return await call_next(request)

    # Inject custom root path if needed (e.g., for reverse proxy deployments)
    @app.middleware("http")
    async def inject_root_path(request, call_next):
        request.scope["root_path"] = "/mcp/servicenow"
        return await call_next(request)

    # Mark initialized on startup
    @app.on_event("startup")
    async def on_startup():
        mark_server_initialized()
        sn_session.mark_initialized()
        logger.info("Startup complete")

    port = int(os.environ.get("PORT", 8005))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
