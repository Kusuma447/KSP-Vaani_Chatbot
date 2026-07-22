from io import BufferedReader
from typing import Any, Dict, List, Optional, TypedDict, Union
from . import validator
from .types import Component
from ._http_client import AuthorizedHttpClient
from .exceptions import CatalystZiaError
from ._constants import Components, RequestMethod, CredentialUser
from .types.zia import (
    ICatalystZiaBarcode,
    ICatalystZiaFace,
    ICatalystZiaFaceComparison,
    ICatalystZiaModeration,
    ICatalystZiaOCR,
    ICatalystZiaObject,
    ICatalystZiaSentimentAnalysisResponse,
    ICatalystZiaKeywordExtractionResponse,
    ICatalystZiaNERPredictionResponse,
    ICatalystZiaTextAnalyticsResponse,
)

ICatalystOCROptions = TypedDict(
    "ICatalystOCROptions",
    {"language": Optional[str], "model_type": Optional[str]},
    total=False,
)

ICatalystBarCodeOptions = TypedDict(
    "ICatalystBarCodeOptions", {"format": Optional[str]}
)

ICatalystImageModerationOpts = TypedDict(
    "ICatalystImageModerationOpt", {"mode": Optional[str]}
)

ICatalystFaceAnalysisOptions = TypedDict(
    "ICatalystFaceAnalysisOptions",
    {
        "mode": Optional[str],
        "emotion": Optional[bool],
        "age": Optional[bool],
        "gender": Optional[bool],
    },
    total=False,
)


class Zia(Component):
    def __init__(self, app):
        self._app = app
        self._requester = AuthorizedHttpClient(app)

    def get_component_name(self):
        return Components.ZIA

    def detect_object(self, file: BufferedReader) -> ICatalystZiaObject:
        self._is_valid_file_type(file)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/detect-object",
            files={"image": file},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def extract_optical_characters(
        self, file: BufferedReader, options: ICatalystOCROptions = None
    ) -> ICatalystZiaOCR:
        self._is_valid_file_type(file)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/ocr",
            files={"image": file},
            data=options,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def extract_aadhaar_characters(
        self, front_img: BufferedReader, back_img: BufferedReader, language: str
    ) -> ICatalystZiaOCR:
        self._is_valid_file_type(front_img, back_img)
        validator.is_non_empty_string(language, "language", CatalystZiaError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/ocr",
            files={"aadhaar_front": front_img, "aadhaar_back": back_img},
            data={"language": language, "model_type": "AADHAAR"},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def scan_barcode(
        self, image: BufferedReader, options: ICatalystBarCodeOptions = None
    ) -> ICatalystZiaBarcode:
        self._is_valid_file_type(image)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/barcode",
            files={"image": image},
            data=options,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def moderate_image(
        self, image: BufferedReader, options: ICatalystImageModerationOpts = None
    ) -> ICatalystZiaModeration:
        self._is_valid_file_type(image)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/imagemoderation",
            files={"image": image},
            data=options,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def analyse_face(
        self, image: BufferedReader, options: ICatalystFaceAnalysisOptions = None
    ) -> ICatalystZiaFace:
        self._is_valid_file_type(image)
        if isinstance(options, dict):
            modified_opt = dict(
                (k, str(v).lower()) for k, v in options.items() if isinstance(v, bool)
            )
            options.update(modified_opt)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/faceanalytics",
            files={"image": image},
            data=options,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def compare_face(
        self, source_img: BufferedReader, query_img: BufferedReader
    ) -> ICatalystZiaFaceComparison:
        self._is_valid_file_type(source_img, query_img)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/facecomparison",
            files={"source_image": source_img, "query_image": query_img},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def auto_ml(self, model_id: Union[int, str], data: Dict[str, Any] = None):
        validator.is_non_empty_string_or_number(model_id, "model_id", CatalystZiaError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f"/ml/automl/model/{model_id}",
            json=data,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    # text analytics apis
    def get_sentiment_analysis(
        self, list_of_docs: List[str], keywords: Optional[List[str]] = None
    ) -> List[ICatalystZiaSentimentAnalysisResponse]:
        validator.is_non_empty_list(list_of_docs, "documents list", CatalystZiaError)
        json_data = {
            "document": list_of_docs,
        }
        if keywords:
            validator.is_non_empty_list(keywords, "keywords", CatalystZiaError)
            json_data["keywords"] = keywords  # adds valid keywords to json_data

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/text-analytics/sentiment-analysis",
            json=json_data,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def get_keyword_extraction(
        self, list_of_docs: List[str]
    ) -> ICatalystZiaKeywordExtractionResponse:
        validator.is_non_empty_list(list_of_docs, "documents list", CatalystZiaError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/text-analytics/keyword-extraction",
            json={"document": list_of_docs},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def get_NER_prediction(  # pylint: disable=invalid-name
        self, list_of_docs: List[str]
    ) -> ICatalystZiaNERPredictionResponse:
        validator.is_non_empty_list(list_of_docs, "documents list", CatalystZiaError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/text-analytics/ner",
            json={"document": list_of_docs},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    def get_text_analytics(
        self, list_of_docs: List[str], keywords: Optional[List[str]] = None
    ) -> ICatalystZiaTextAnalyticsResponse:
        validator.is_non_empty_list(list_of_docs, "documents list", CatalystZiaError)
        json_data = {"document": list_of_docs}
        if keywords:
            validator.is_non_empty_list(keywords, "keywords", CatalystZiaError)
            json_data["keywords"] = keywords  # adds valid keywords to json_data

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/ml/text-analytics",
            json=json_data,
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")

    @staticmethod
    def _is_valid_file_type(*files):
        for file in files:
            if not isinstance(file, BufferedReader):
                raise CatalystZiaError(
                    "Invalid-Argument", "File must be a instance of BufferReader"
                )
