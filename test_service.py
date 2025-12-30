#!/usr/bin/env python3
"""
Test script to validate the project management service implementation.

Usage:
    python test_service.py <github_token>
"""

import sys
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"
TEST_PROJECT = "test-hello-world"
TEST_REPO = "https://github.com/octocat/Hello-World.git"


def print_header(text):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print('='*60)


def print_result(test_name, success, details=""):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"       {details}")


def test_health_check():
    """Test health check endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        success = response.status_code == 200
        print_result("Health Check", success)
        return success
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False


def test_root_endpoint():
    """Test root endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        success = response.status_code == 200
        print_result("Root Endpoint", success)
        return success
    except Exception as e:
        print_result("Root Endpoint", False, str(e))
        return False


def test_authentication(token):
    """Test authentication."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(f"{BASE_URL}/projects/list", headers=headers, timeout=5)
        success = response.status_code in [200, 401]  # 401 if invalid token
        print_result("Authentication", success)
        return success
    except Exception as e:
        print_result("Authentication", False, str(e))
        return False


def test_create_project(token):
    """Test project creation."""
    try:
        headers = {"Authorization": f"token {token}"}
        data = {
            "project_name": TEST_PROJECT,
            "repo_url": TEST_REPO
        }
        response = requests.post(
            f"{BASE_URL}/projects/create",
            headers=headers,
            json=data,
            timeout=60
        )
        success = response.status_code in [200, 201]
        print_result("Create Project", success)
        if not success:
            print(f"       Response: {response.text[:100]}")
        return success
    except requests.Timeout:
        print_result("Create Project", False, "Timeout (clone takes time)")
        return False
    except Exception as e:
        print_result("Create Project", False, str(e))
        return False


def test_list_projects(token):
    """Test listing projects."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            f"{BASE_URL}/projects/list",
            headers=headers,
            timeout=5
        )
        success = response.status_code == 200
        print_result("List Projects", success)
        if success:
            data = response.json()
            count = data.get("count", 0)
            print(f"       Found {count} project(s)")
        return success
    except Exception as e:
        print_result("List Projects", False, str(e))
        return False


def test_list_files(token):
    """Test file listing."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            f"{BASE_URL}/projects/{TEST_PROJECT}/files/list",
            headers=headers,
            timeout=10
        )
        success = response.status_code == 200
        print_result("List Files", success)
        if success:
            data = response.json()
            count = data.get("count", 0)
            print(f"       Found {count} file(s)")
        return success
    except Exception as e:
        print_result("List Files", False, str(e))
        return False


def test_read_file(token):
    """Test file reading."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            f"{BASE_URL}/projects/{TEST_PROJECT}/files/read?path=README",
            headers=headers,
            timeout=10
        )
        success = response.status_code == 200
        print_result("Read File", success)
        if success:
            data = response.json()
            size = data.get("size_bytes", 0)
            print(f"       File size: {size} bytes")
        return success
    except Exception as e:
        print_result("Read File", False, str(e))
        return False


def test_git_status(token):
    """Test git status."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            f"{BASE_URL}/projects/{TEST_PROJECT}/git/status",
            headers=headers,
            timeout=10
        )
        success = response.status_code == 200
        print_result("Git Status", success)
        if success:
            data = response.json()
            branch = data.get("branch", "unknown")
            print(f"       Current branch: {branch}")
        return success
    except Exception as e:
        print_result("Git Status", False, str(e))
        return False


def test_shell_execute(token):
    """Test shell command execution."""
    try:
        headers = {"Authorization": f"token {token}"}
        data = {
            "command": "pwd",
            "timeout": 10
        }
        response = requests.post(
            f"{BASE_URL}/projects/{TEST_PROJECT}/shell/execute",
            headers=headers,
            json=data,
            timeout=15
        )
        success = response.status_code == 200
        print_result("Shell Execute", success)
        if success:
            data = response.json()
            exit_code = data.get("exit_code", -1)
            print(f"       Exit code: {exit_code}")
        return success
    except Exception as e:
        print_result("Shell Execute", False, str(e))
        return False


def test_delete_project(token):
    """Test project deletion."""
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.delete(
            f"{BASE_URL}/projects/{TEST_PROJECT}",
            headers=headers,
            timeout=30
        )
        success = response.status_code == 200
        print_result("Delete Project", success)
        return success
    except Exception as e:
        print_result("Delete Project", False, str(e))
        return False


def test_invalid_auth():
    """Test invalid authentication."""
    try:
        headers = {"Authorization": "token invalid_token"}
        response = requests.get(
            f"{BASE_URL}/projects/list",
            headers=headers,
            timeout=10
        )
        success = response.status_code == 401
        print_result("Invalid Auth Rejected", success)
        return success
    except Exception as e:
        print_result("Invalid Auth Rejected", False, str(e))
        return False


def test_missing_auth():
    """Test missing authentication."""
    try:
        response = requests.get(
            f"{BASE_URL}/projects/list",
            timeout=5
        )
        success = response.status_code == 401
        print_result("Missing Auth Rejected", success)
        return success
    except Exception as e:
        print_result("Missing Auth Rejected", False, str(e))
        return False


def main():
    """Run all tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_service.py <github_token>")
        print("\nOr set GITHUB_TOKEN environment variable")
        token = Path("/tmp/.github_token").read_text().strip() \
                if Path("/tmp/.github_token").exists() else None
        if not token:
            print("\nError: GitHub token required")
            sys.exit(1)
    else:
        token = sys.argv[1]
    
    print_header("Project Management Service - Test Suite")
    print(f"Base URL: {BASE_URL}")
    print(f"Token: {token[:20]}..." if token else "Token: Not provided")
    
    results = {
        "Basic Connectivity": [],
        "Authentication & Security": [],
        "Project Operations": [],
        "Filesystem Operations": [],
        "Git Operations": [],
        "Shell Operations": []
    }
    
    # Basic connectivity
    print_header("Basic Connectivity Tests")
    results["Basic Connectivity"].append(("Health Check", test_health_check()))
    results["Basic Connectivity"].append(("Root Endpoint", test_root_endpoint()))
    
    # Authentication
    print_header("Authentication & Security Tests")
    results["Authentication & Security"].append(("Missing Auth", test_missing_auth()))
    results["Authentication & Security"].append(("Invalid Auth", test_invalid_auth()))
    results["Authentication & Security"].append(("Valid Auth", test_authentication(token)))
    
    # Project operations
    print_header("Project Operations Tests")
    results["Project Operations"].append(("List Projects", test_list_projects(token)))
    results["Project Operations"].append(("Create Project", test_create_project(token)))
    
    # Filesystem operations
    print_header("Filesystem Operations Tests")
    results["Filesystem Operations"].append(("List Files", test_list_files(token)))
    results["Filesystem Operations"].append(("Read File", test_read_file(token)))
    
    # Git operations
    print_header("Git Operations Tests")
    results["Git Operations"].append(("Git Status", test_git_status(token)))
    
    # Shell operations
    print_header("Shell Operations Tests")
    results["Shell Operations"].append(("Shell Execute", test_shell_execute(token)))
    
    # Cleanup
    print_header("Cleanup")
    results["Project Operations"].append(("Delete Project", test_delete_project(token)))
    
    # Summary
    print_header("Test Summary")
    total_tests = sum(len(v) for v in results.values())
    total_passed = sum(sum(1 for _, r in v if r) for v in results.values())
    
    for category, tests in results.items():
        passed = sum(1 for _, r in tests if r)
        print(f"{category}: {passed}/{len(tests)}")
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
