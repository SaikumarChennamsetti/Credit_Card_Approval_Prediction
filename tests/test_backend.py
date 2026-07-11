import unittest
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.app import create_app
from backend.models import db, PredictionHistory, User
from backend.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test_secret_key_session'

class TestBackendAPI(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def register_and_login(self, username="testuser", email="test@test.com", password="password123"):
        reg_payload = {
            "full_name": "Test User",
            "email": email,
            "username": username,
            "mobile": "1234567890",
            "password": password,
            "confirm_password": password
        }
        self.client.post(
            '/api/signup',
            data=json.dumps(reg_payload),
            content_type='application/json'
        )
        login_payload = {
            "username_or_email": username,
            "password": password,
            "remember_me": False
        }
        self.client.post(
            '/api/login',
            data=json.dumps(login_payload),
            content_type='application/json'
        )

    def test_unauthorized_access_redirects(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_unauthorized_api_access_rejected(self):
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "UNAUTHORIZED")

    def test_root_route(self):
        self.register_and_login()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_api_welcome(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["version"], "1.0.0")

    def test_health_endpoint(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "healthy")

    def test_predict_success(self):
        self.register_and_login()
        payload = {
            "applicant_id": "T-001",
            "CODE_GENDER": "M",
            "FLAG_OWN_CAR": "Y",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": 180000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 35.5,
            "EMPLOYED_YEARS": 4.5,
            "OCCUPATION_TYPE": "Managers",
            "CNT_FAM_MEMBERS": 2
        }
        response = self.client.post(
            '/api/predict',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("approved", data["data"])
        self.assertIn("record_id", data["data"])

    def test_predict_invalid_validation(self):
        self.register_and_login()
        payload = {
            "CODE_GENDER": "X",
            "FLAG_OWN_CAR": "Y",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": -1,
            "AMT_INCOME_TOTAL": 180000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 15.0,
            "EMPLOYED_YEARS": 4.5,
            "OCCUPATION_TYPE": "Managers",
            "CNT_FAM_MEMBERS": 1
        }
        response = self.client.post(
            '/api/predict',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 422)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "VALIDATION_FAILED")
        self.assertTrue(len(data["data"]["validation_details"]) > 0)

    def test_predict_invalid_json(self):
        self.register_and_login()
        response = self.client.post(
            '/api/predict',
            data="invalid_raw_string",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "INVALID_JSON")

    def test_get_history_paginated(self):
        self.register_and_login()
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("records", data["data"])

    def test_delete_record_not_found(self):
        self.register_and_login()
        response = self.client.delete('/api/history/9999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "RECORD_NOT_FOUND")

    def test_history_isolation_between_users(self):
        self.register_and_login(username="usera", email="usera@test.com")
        payload = {
            "applicant_id": "A-001",
            "CODE_GENDER": "M",
            "FLAG_OWN_CAR": "Y",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": 180000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 35.5,
            "EMPLOYED_YEARS": 4.5,
            "OCCUPATION_TYPE": "Managers",
            "CNT_FAM_MEMBERS": 2
        }
        res_a = self.client.post(
            '/api/predict',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data_a = json.loads(res_a.data)
        record_id = data_a["data"]["record_id"]
        
        res_history_a = self.client.get('/api/history')
        hist_data_a = json.loads(res_history_a.data)
        self.assertEqual(len(hist_data_a["data"]["records"]), 1)
        self.assertEqual(hist_data_a["data"]["records"][0]["id"], record_id)
        
        self.client.post('/api/logout')
        self.register_and_login(username="userb", email="userb@test.com")
        
        res_history_b = self.client.get('/api/history')
        hist_data_b = json.loads(res_history_b.data)
        self.assertEqual(len(hist_data_b["data"]["records"]), 0)
        
        res_detail_b = self.client.get(f'/api/history/{record_id}')
        self.assertEqual(res_detail_b.status_code, 404)
        
        res_delete_b = self.client.delete(f'/api/history/{record_id}')
        self.assertEqual(res_delete_b.status_code, 404)

if __name__ == '__main__':
    unittest.main()
