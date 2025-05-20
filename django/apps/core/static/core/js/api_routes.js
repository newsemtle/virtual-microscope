const API_BASE_URL = "/api";

const API_ROUTES = {
    accounts: (() => {
        const base = `${API_BASE_URL}/accounts`;
        return {
            list: {
                base: `${base}/`,
                login: `${base}/login/`,
                logout: `${base}/logout/`,
                session_extend: `${base}/session_extend/`,
                session_time: `${base}/session_time/`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                };
            },
        };
    })(),
    slides: (() => {
        const base = `${API_BASE_URL}/images/slides`;
        return {
            list: {
                base: `${base}/`,
                search: (query) => `${base}/dbsearch/?search=${query}`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                    dzi: `${detailBase}.dzi/`,
                    file: `${detailBase}/file/`,
                    thumbnail: `${detailBase}/thumbnail/`,
                    associated_image: (filename) => `${detailBase}/associated_image/${filename}/`,
                    annotations: `${detailBase}/annotations/`,
                    rebuild: `${detailBase}/rebuild/`,
                };
            },
        };
    })(),
    imageFolders: (() => {
        const base = `${API_BASE_URL}/images/folders`;
        return {
            list: {
                base: `${base}/`,
                tree: `${base}/tree/`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                    items: `${detailBase}/items/`,
                };
            },
        };
    })(),
    lectures: (() => {
        const base = `${API_BASE_URL}/lectures/lectures`;
        return {
            list: {
                base: `${base}/`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                    toggle_status: `${detailBase}/toggle_status/`,
                    duplicate: `${detailBase}/duplicate/`,
                    send: `${detailBase}/send/`,
                };
            },
        };
    })(),
    lectureFolders: (() => {
        const base = `${API_BASE_URL}/lectures/folders`;
        return {
            list: {
                base: `${base}/`,
                tree: `${base}/tree/`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                };
            },
        };
    })(),
    annotations: (() => {
        const base = `${API_BASE_URL}/viewer/annotations`;
        return {
            list: {
                base: `${base}/`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                };
            },
        };
    })(),
};
