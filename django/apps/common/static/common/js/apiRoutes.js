const API_BASE_URL = '/api';

const API_ROUTES = {
    accounts: `${API_BASE_URL}/accounts/`,
    slides: `${API_BASE_URL}/images/slides/`,
    slideDetail: (id) => {
        const base = `${API_BASE_URL}/images/slides/${id}/`;
        return {
            base,
            annotations: `${base}annotations/`,
            thumbnail: `${base}thumbnail/`,
            associated_image: `${base}associated_image/`,
        }
    },
    imageFolders: `${API_BASE_URL}/images/folders/`,
    imageFolderDetail: (id) => {
        const base = `${API_BASE_URL}/images/folders/${id}/`;
        return {
            base,
            tree: `${base}tree/`,
            items: `${base}items/`,
        }
    },
    lectures: `${API_BASE_URL}/lectures/lectures/`,
    lectureDetail: (id) => {
        const base = `${API_BASE_URL}/lectures/lectures/${id}/`;
        return {
            base,
            toggle_activity: `${base}toggle_activity/`,
            duplicate: `${base}duplicate/`,
            send: `${base}send/`,
        }
    },
    lectureFolders: `${API_BASE_URL}/lectures/folders/`,
    lectureFolderDetail: (id) => {
        const base = `${API_BASE_URL}/lectures/folders/${id}/`;
        return {
            base,
            tree: `${base}tree/`,
        }
    },
    annotations: `${API_BASE_URL}/viewer/annotations/`,
}