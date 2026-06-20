export function parseInput(raw) {
    let data = [];
    if (raw) {
        if (raw.startsWith('[')) {
            data = JSON.parse(raw);
        } else {
            data = raw.split(',').map(s => s.trim()).filter(Boolean);
        }
    }
    return data;
}

export function formatResult(result) {
    if (!result) return '';
    if (result.ok && result.ok === true) {
        if (result.data && result.data.length > 10) {
            return result.data.slice(0, 10).join(',') + '...';
        }
    }
    return String(result);
}
