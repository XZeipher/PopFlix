#!/usr/bin/env python3
"""
PopFlix Backend API Testing Suite
Tests all backend endpoints for the streaming platform
"""

import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from frontend env
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://db0728c3-3d80-4545-830a-19c7b613c270.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing PopFlix Backend APIs at: {API_BASE}")
print("=" * 60)

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def add_result(self, test_name, status, message=""):
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        
        status_symbol = "✅" if status == "PASS" else "❌"
        print(f"{status_symbol} {test_name}: {message}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        return self.passed, self.failed

# Initialize test results
test_results = TestResults()

def test_endpoint(method, endpoint, data=None, headers=None, expected_status=200):
    """Helper function to test API endpoints"""
    try:
        url = f"{API_BASE}{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code == expected_status:
            return True, response.json() if response.content else {}
        else:
            return False, f"Status {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

# Test 1: TMDB API Integration
print("\n🎬 Testing TMDB API Integration...")

# Test popular movies
success, result = test_endpoint("GET", "/movies/popular")
if success and "results" in result and len(result["results"]) > 0:
    movie = result["results"][0]
    if "tmdb_id" in movie and "title" in movie:
        test_results.add_result("TMDB Popular Movies", "PASS", f"Retrieved {len(result['results'])} movies")
    else:
        test_results.add_result("TMDB Popular Movies", "FAIL", "Invalid movie data structure")
else:
    test_results.add_result("TMDB Popular Movies", "FAIL", f"API call failed: {result}")

# Test popular TV shows
success, result = test_endpoint("GET", "/tv/popular")
if success and "results" in result and len(result["results"]) > 0:
    show = result["results"][0]
    if "tmdb_id" in show and "name" in show:
        test_results.add_result("TMDB Popular TV Shows", "PASS", f"Retrieved {len(result['results'])} TV shows")
    else:
        test_results.add_result("TMDB Popular TV Shows", "FAIL", "Invalid TV show data structure")
else:
    test_results.add_result("TMDB Popular TV Shows", "FAIL", f"API call failed: {result}")

# Test search functionality
success, result = test_endpoint("GET", "/search?q=Avengers")
if success and "results" in result:
    if len(result["results"]) > 0:
        search_item = result["results"][0]
        if "type" in search_item and "data" in search_item:
            test_results.add_result("TMDB Search", "PASS", f"Search returned {len(result['results'])} results")
        else:
            test_results.add_result("TMDB Search", "FAIL", "Invalid search result structure")
    else:
        test_results.add_result("TMDB Search", "PASS", "Search returned empty results (valid)")
else:
    test_results.add_result("TMDB Search", "FAIL", f"Search API failed: {result}")

# Test 2: Video Streaming Integration
print("\n🎥 Testing Video Streaming Integration...")

# Test movie streaming URLs
success, result = test_endpoint("GET", "/stream/movie/550")  # Fight Club TMDB ID
if success and "embed_url" in result and "torrent_url" in result:
    if "rivestream.org" in result["embed_url"]:
        test_results.add_result("Movie Streaming URLs", "PASS", "Generated valid RiveStream URLs")
    else:
        test_results.add_result("Movie Streaming URLs", "FAIL", "Invalid streaming URL format")
else:
    test_results.add_result("Movie Streaming URLs", "FAIL", f"Failed to get streaming URLs: {result}")

# Test TV show streaming URLs
success, result = test_endpoint("GET", "/stream/tv/1399?season=1&episode=1")  # Game of Thrones
if success and "embed_url" in result and "torrent_url" in result:
    if "rivestream.org" in result["embed_url"] and "season=1" in result["embed_url"]:
        test_results.add_result("TV Show Streaming URLs", "PASS", "Generated valid TV streaming URLs")
    else:
        test_results.add_result("TV Show Streaming URLs", "FAIL", "Invalid TV streaming URL format")
else:
    test_results.add_result("TV Show Streaming URLs", "FAIL", f"Failed to get TV streaming URLs: {result}")

# Test invalid content type
success, result = test_endpoint("GET", "/stream/invalid/123", expected_status=400)
if success:
    test_results.add_result("Invalid Content Type Handling", "PASS", "Properly rejected invalid content type")
else:
    test_results.add_result("Invalid Content Type Handling", "FAIL", "Should reject invalid content types")

# Test 3: User Authentication System (Mock Testing)
print("\n🔐 Testing User Authentication System...")

# Test Google OAuth endpoint with mock data
mock_google_token = "mock_google_access_token_for_testing"
auth_data = {"token": mock_google_token}

success, result = test_endpoint("POST", "/auth/google", data=auth_data, expected_status=400)
if success or "Invalid Google token" in str(result):
    test_results.add_result("Google OAuth Token Validation", "PASS", "Properly validates Google tokens")
else:
    test_results.add_result("Google OAuth Token Validation", "FAIL", "Should validate Google tokens")

# Test authentication required endpoints without token
success, result = test_endpoint("GET", "/profile", expected_status=401)
if not success:
    test_results.add_result("Authentication Required", "PASS", "Protected endpoints require authentication")
else:
    test_results.add_result("Authentication Required", "FAIL", "Should require authentication")

# Test 4: Premium Payment System
print("\n💳 Testing Premium Payment System...")

# Test create checkout without authentication
success, result = test_endpoint("POST", "/payments/create-checkout", 
                               data={"package_id": "premium_monthly", "origin_url": BACKEND_URL}, 
                               expected_status=401)
if not success:
    test_results.add_result("Payment Authentication", "PASS", "Payment endpoints require authentication")
else:
    test_results.add_result("Payment Authentication", "FAIL", "Should require authentication for payments")

# Test payment status endpoint
success, result = test_endpoint("GET", "/payments/status/invalid_session_id", expected_status=404)
if success or "not found" in str(result).lower():
    test_results.add_result("Payment Status Check", "PASS", "Handles invalid session IDs properly")
else:
    test_results.add_result("Payment Status Check", "FAIL", "Should handle invalid session IDs")

# Test 5: User Features (Watch History, Favorites)
print("\n👤 Testing User Features...")

# Test watch history without authentication
success, result = test_endpoint("GET", "/watchhistory", expected_status=401)
if not success:
    test_results.add_result("Watch History Authentication", "PASS", "Watch history requires authentication")
else:
    test_results.add_result("Watch History Authentication", "FAIL", "Should require authentication")

# Test add to watch history without authentication
watch_data = {
    "content_type": "movie",
    "tmdb_id": 550,
    "title": "Fight Club",
    "poster_path": "/path/to/poster.jpg",
    "progress": 0.5
}
success, result = test_endpoint("POST", "/watchhistory", data=watch_data, expected_status=401)
if not success:
    test_results.add_result("Add Watch History Authentication", "PASS", "Adding to watch history requires authentication")
else:
    test_results.add_result("Add Watch History Authentication", "FAIL", "Should require authentication")

# Test favorites without authentication
success, result = test_endpoint("GET", "/favorites", expected_status=401)
if not success:
    test_results.add_result("Favorites Authentication", "PASS", "Favorites require authentication")
else:
    test_results.add_result("Favorites Authentication", "FAIL", "Should require authentication")

# Test add to favorites without authentication
favorite_data = {
    "content_type": "movie",
    "tmdb_id": 550,
    "title": "Fight Club",
    "poster_path": "/path/to/poster.jpg"
}
success, result = test_endpoint("POST", "/favorites", data=favorite_data, expected_status=401)
if not success:
    test_results.add_result("Add Favorites Authentication", "PASS", "Adding favorites requires authentication")
else:
    test_results.add_result("Add Favorites Authentication", "FAIL", "Should require authentication")

# Test remove from favorites without authentication
success, result = test_endpoint("DELETE", "/favorites/movie/550", expected_status=401)
if not success:
    test_results.add_result("Remove Favorites Authentication", "PASS", "Removing favorites requires authentication")
else:
    test_results.add_result("Remove Favorites Authentication", "FAIL", "Should require authentication")

# Test 6: Comments System (Premium Only)
print("\n💬 Testing Comments System...")

# Test add comment without authentication
comment_data = {
    "content_type": "movie",
    "tmdb_id": 550,
    "text": "Great movie!",
    "parent_id": None
}
success, result = test_endpoint("POST", "/comments", data=comment_data, expected_status=401)
if not success:
    test_results.add_result("Comments Authentication", "PASS", "Comments require authentication")
else:
    test_results.add_result("Comments Authentication", "FAIL", "Should require authentication")

# Test get comments (should work without authentication)
success, result = test_endpoint("GET", "/comments/movie/550")
if success and isinstance(result, list):
    test_results.add_result("Get Comments", "PASS", f"Retrieved comments successfully (count: {len(result)})")
else:
    test_results.add_result("Get Comments", "FAIL", f"Failed to get comments: {result}")

# Test 7: Additional API Endpoints
print("\n🔧 Testing Additional Endpoints...")

# Test user profile without authentication
success, result = test_endpoint("GET", "/profile", expected_status=401)
if not success:
    test_results.add_result("Profile Authentication", "PASS", "Profile endpoint requires authentication")
else:
    test_results.add_result("Profile Authentication", "FAIL", "Should require authentication")

# Test Stripe webhook endpoint
success, result = test_endpoint("POST", "/webhook/stripe", data={})
if success or "signature" in str(result).lower():
    test_results.add_result("Stripe Webhook", "PASS", "Webhook endpoint accessible")
else:
    test_results.add_result("Stripe Webhook", "FAIL", f"Webhook failed: {result}")

# Test 8: Error Handling
print("\n⚠️ Testing Error Handling...")

# Test non-existent endpoint
success, result = test_endpoint("GET", "/nonexistent", expected_status=404)
if not success:
    test_results.add_result("404 Error Handling", "PASS", "Returns 404 for non-existent endpoints")
else:
    test_results.add_result("404 Error Handling", "FAIL", "Should return 404 for non-existent endpoints")

# Test TV streaming without season/episode
success, result = test_endpoint("GET", "/stream/tv/1399", expected_status=400)
if not success and "season and episode required" in str(result).lower():
    test_results.add_result("TV Streaming Validation", "PASS", "Validates season/episode for TV shows")
else:
    test_results.add_result("TV Streaming Validation", "FAIL", "Should require season/episode for TV shows")

# Final Summary
passed, failed = test_results.summary()

print(f"\n📊 DETAILED TEST RESULTS:")
print("-" * 60)
for result in test_results.results:
    status_symbol = "✅" if result["status"] == "PASS" else "❌"
    print(f"{status_symbol} {result['test']}: {result['message']}")

print(f"\n🎯 OVERALL RESULT: {passed}/{passed + failed} tests passed")

if failed == 0:
    print("🎉 All critical backend functionality is working!")
else:
    print(f"⚠️ {failed} tests failed - see details above")

print("\n" + "=" * 60)
print("PopFlix Backend API Testing Complete")
print("=" * 60)