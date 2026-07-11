import unittest
import sys
import os
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import (
    PROCESSED_DATA_PATH,
    MODEL_PATH,
    PREPROCESSOR_PATH,
    TARGET_COL
)
from backend.services import execute_prediction, load_production_model_assets

class TestMLPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        load_production_model_assets(str(MODEL_PATH), str(PREPROCESSOR_PATH))

    def test_processed_dataset_integrity(self):
        self.assertTrue(PROCESSED_DATA_PATH.exists())
        df = pd.read_csv(PROCESSED_DATA_PATH)
        self.assertIn(TARGET_COL, df.columns)
        self.assertTrue(len(df) > 0)

    def test_preprocessor_load(self):
        preprocessor = joblib.load(PREPROCESSOR_PATH)
        self.assertIsNotNone(preprocessor)
        self.assertTrue(hasattr(preprocessor, "transform"))

    def test_model_load(self):
        model = joblib.load(MODEL_PATH)
        self.assertIsNotNone(model)
        self.assertTrue(hasattr(model, "predict"))

    def test_prediction_inference_success(self):
        sample_input = {
            "CODE_GENDER": "F",
            "FLAG_OWN_CAR": "N",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": 1,
            "AMT_INCOME_TOTAL": 150000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_FAMILY_STATUS": "Civil marriage",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 29.0,
            "EMPLOYED_YEARS": 3.0,
            "OCCUPATION_TYPE": "Core staff",
            "CNT_FAM_MEMBERS": 3
        }
        res = execute_prediction(sample_input)
        self.assertIn("approved", res)
        self.assertIn("probability", res)
        self.assertIn("confidence_score", res)
        self.assertIn("risk_level", res)
        
        self.assertTrue(0.0 <= res["probability"] <= 1.0)
        self.assertTrue(0.0 <= res["confidence_score"] <= 1.0)

    def test_prediction_inference_edge_case(self):
        edge_input = {
            "CODE_GENDER": "M",
            "FLAG_OWN_CAR": "Y",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": 1000000,
            "NAME_INCOME_TYPE": "Pensioner",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Single / not married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 75.0,
            "EMPLOYED_YEARS": 0.0,
            "OCCUPATION_TYPE": "Unspecified",
            "CNT_FAM_MEMBERS": 1
        }
        res = execute_prediction(edge_input)
        self.assertIn("approved", res)
        self.assertTrue(isinstance(res["approved"], bool))

if __name__ == '__main__':
    unittest.main()
