# pylint: disable=invalid-name
from typing import List, Optional, TypedDict, Dict, Literal


class ObjectParams(TypedDict):
    co_ordinates: List[int]
    object_type: str
    confidence: str


class ICatalystZiaObject(TypedDict):
    object: List[ObjectParams]


class ICatalystZiaOCR(TypedDict):
    confidence: Optional[str]
    text: str


class ICatalystZiaBarcode(TypedDict):
    content: str


class ICatalystZiaModeration(TypedDict):
    probability: Dict[str, str]
    confidence: int
    prediction: str


class ICatalystZiaCom(TypedDict):
    prediction: str
    confidence: Dict[str, str]


class FaceParams(TypedDict):
    confidence: int
    id: str
    co_ordinates: List[int]
    emotion: ICatalystZiaCom
    age: ICatalystZiaCom
    gender: ICatalystZiaCom
    landmarks: Optional[Dict[str, List[int]]]


class ICatalystZiaFace(TypedDict):
    faces: List[FaceParams]


class ICatalystZiaFaceComparison(TypedDict):
    confidence: Optional[int]
    matched: bool


class ICatalystZiaAutoML(TypedDict):
    regression_result: Optional[int]
    classification_result: Optional[Dict[str, int]]


# Text analysis response
class ConfidenceScores(TypedDict):
    negative: int
    neutral: int
    positive: int


class ICatalystZiaAnalytics(TypedDict):
    sentiment: Literal["Positive", "Negative", "Neutral"]
    confidence_scores: ConfidenceScores


class ICatalystZiaSentenceAnalytics(ICatalystZiaAnalytics):
    sentence: str


class ICatalystZiaKeywordAnalytics(ICatalystZiaAnalytics):
    keyword: str


class ICatalystZiaSentimentAnalysis(TypedDict):
    document_sentiment: str
    sentence_analytics: List[ICatalystZiaSentenceAnalytics]
    keyword_analytics: List[ICatalystZiaKeywordAnalytics]
    overall_score: float


class ICatalystZiaSentimentAnalysisResponse(TypedDict):
    sentiment_prediction: List[ICatalystZiaSentimentAnalysis]


class ICatalystZiaExtractedKeywords(TypedDict):
    keywords: List[str]
    keyphrases: List[str]


class ICatalystZiaKeywordExtractionResponse(TypedDict):
    keyword_extractor: ICatalystZiaExtractedKeywords


class ICatalystZiaNer(TypedDict):
    start_index: int
    confidence_score: int
    end_index: int
    ner_tag: str
    token: str


class ICatalystZiaNerGeneralEntities(TypedDict):
    general_entities: List[ICatalystZiaNer]


class ICatalystZiaNERPredictionResponse(TypedDict):
    ner: ICatalystZiaNerGeneralEntities


class ICatalystZiaTextAnalyticsResponse(
    ICatalystZiaNERPredictionResponse,
    ICatalystZiaKeywordExtractionResponse,
    ICatalystZiaSentimentAnalysisResponse,
):
    pass
