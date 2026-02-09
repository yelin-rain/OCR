import axios from 'axios';

// Create a configured axios instance
export const httpClient = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 30000,
});

// Add a request interceptor
httpClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add a response interceptor to handle 401s (optional but good practice)
httpClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('token');
            // We might want to redirect to login here, but since this is a provider, 
            // we rely on the UI components (like PrivateRoute or AuthContext) to handle the null token.
            // window.location.href = '/login'; // simple force redirect
        }
        return Promise.reject(error);
    }
);
