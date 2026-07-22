from typing import Literal, TypedDict, Union, List, Dict
from ..types import ICatalystGResponse

PdfFormats = Literal[
    'Letter', 'Legal', 'Tabloid', 'Ledger',
    'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6'
]

PdfMargin = TypedDict('PdfMargin', {
    'top': str,
    'bottom': str,
    'left': str,
    'right': str
}, total=False)


class PdfOptions(TypedDict, total=False):
    scale: Union[int,str]
    display_header_footer: bool
    header_template: str
    password: str
    footer_template: str
    print_background: bool
    landscape: bool
    page_ranges: Union[int,str]
    format: PdfFormats
    width: Union[int,str]
    height: Union[int,str]
    margin: PdfMargin


CssContent = TypedDict('CssContent', {
    'content': str
})

CssUrl = TypedDict('CssUrl', {
    'url': str
})

JsContent = TypedDict('JsContent', {
    'content': str
})

JsUrl = TypedDict('JsUrl', {
    'url': str
})

PdfViewPort = TypedDict('PdfViewPort', {
    "width": Union[int,str],
    "height": Union[int,str]
})


class PdfPageOptions(TypedDict, total=False):
    css: Union[CssContent, CssUrl]
    js: Union[JsContent, JsUrl] # pylint: disable=invalid-name
    viewport: PdfViewPort
    javascript_enabled: bool


class ScreenShotOptions(TypedDict, total=False):
    type: Literal['jpeg', 'png']
    quality: Union[int, str]
    full_page: bool
    omit_background: bool
    capture_beyond_viewport: bool


class ScreenShotPageOptions(TypedDict):
    device: str


class NavigationOptions(TypedDict, total=False):
    timeout: Union[int,str]
    wait_until: Literal['load', 'domcontentloaded', 'networkidle0', 'networkidle2']

class OutputOptions(TypedDict):
    output_type: Literal['pdf', 'screenshot']

class DataverseSimilarCompanyReq(TypedDict, total = False):
    lead_name: str
    website_url: str

class DataverseEnrichLeadReq(DataverseSimilarCompanyReq, total = False):
    email: str

OrgHeadquarters = TypedDict('OrgHeadquarters', {
    'city': str,
    'country': str,
    'state': str,
    'id': str,
    'street':str,
    'pincode':str
}, total=False)

class DataverseLead(TypedDict, total = False):
    organization_name: str
    description: str
    employee_count: str
    revenue: str
    organization_type: str
    organization_status: str
    email: List[str]
    address: List[str]
    contact: List[str]
    industries: Dict[str, str]
    social: Dict[str, str]
    founding_year: str
    years_in_industry: str
    territory: List[str]
    headquarters: List[OrgHeadquarters]
    ceo: str
    logo: str
    about_us: str
    website: str
    website_status: str
    business_model: List[str]
    sign_in_link: str
    sign_up_link: str
    source_language: str

class DataverseTechStack(TypedDict, total = False):
    organization_name: str
    website: str
    website_status: str
    technographic_data: Dict[str, None]

class BrowserGridDetails(ICatalystGResponse):
    browser_version: Dict[str, str]
    config_type: int
    endpoint_type: int
    id: str
    max_nodes_count: int
    max_sessions_count: int
    memory: int
    name: str

class BrowserGridNode(TypedDict):
    node_count: int
    session_count: int
    session_queue_size: int
