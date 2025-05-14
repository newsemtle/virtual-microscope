const API_BASE_URL = '/api';

const API_ROUTES = {
    accounts: `${API_BASE_URL}/accounts/`,
    slides: `${API_BASE_URL}/images/slides/`,
    slideDetail: (id) => `${API_BASE_URL}/images/slides/${id}/`,
    imageFolders: `${API_BASE_URL}/images/folders/`,
    imageFolderDetail: (id) => `${API_BASE_URL}/images/folders/${id}/`,
    lectures: `${API_BASE_URL}/lectures/lectures/`,
    lectureDetail: (id) => `${API_BASE_URL}/lectures/lectures/${id}/`,
    lectureFolders: `${API_BASE_URL}/lectures/folders/`,
    lectureFolderDetail: (id) => `${API_BASE_URL}/lectures/folders/${id}/`,
    annotations: `${API_BASE_URL}/viewer/annotations/`,
}