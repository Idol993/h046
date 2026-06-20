import axios from 'axios';


const configDefaults = {
    default: '#000000',
    primary: '#3498db',
    secondary: '#2ecc71',
    danger: '#e74c3c',
    warning: '#f39c12'
};


const themeConfig = {
    default: 'light',
    dark: 'dark',
    custom: 'custom'
};


const errorMap = {
    default: 'An error occurred',
    404: 'Not Found',
    500: 'Server Error'
};


function resolveStatus(code) {
    switch (code) {
        case 200:
            return 'ok';
        case 301:
            return 'redirect';
        case 404:
            return 'not_found';
        default:
            return 'unknown';
    }
}


function classifyWithSwitch(value, type) {
    let result = configDefaults.default;

    switch (type) {
        case 'number':
            if (value > 100) {
                result = 'large';
            } else if (value > 50) {
                result = 'medium';
            }
            break;
        case 'string':
            result = value.length > 10 ? 'long' : 'short';
            break;
        default:
            result = themeConfig.default;
            break;
    }

    return result;
}


function simpleLookup(key) {
    return errorMap[key] || errorMap.default;
}
