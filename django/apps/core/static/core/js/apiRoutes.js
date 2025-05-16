const API_BASE_URL = "/api";

const API_ROUTES = {
    accounts: (() => {
        const base = `${API_BASE_URL}/accounts`;
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
    slides: (() => {
        const base = `${API_BASE_URL}/images/slides`;
        return {
            list: {
                base: `${base}/`,
                search: (query) => `${base}/?search=${query}`,
            },
            detail: (id) => {
                const detailBase = `${base}/${id}`;
                return {
                    base: `${detailBase}/`,
                    annotations: `${detailBase}/annotations/`,
                    thumbnail: `${detailBase}/thumbnail/`,
                    associated_image: (filename) => `${detailBase}/associated_image/${filename}/`,
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
        const base = `${API_BASE_URL}/annotations`;
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
