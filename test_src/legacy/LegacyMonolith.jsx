import React, { Component } from 'react';
import axios from 'axios';
import _ from 'lodash';
import { connect } from 'react-redux';
import { withRouter } from 'react-router';
import moment from 'moment';
import classNames from 'classnames';
import { Table, Button, Modal, Form, Input, Select, Pagination } from 'antd';
import { DownloadOutlined, UploadOutlined, DeleteOutlined } from '@ant-design/icons';


class LegacyMonolithPage extends Component {

    constructor(props) {
        super(props);
        this.state = {
            loading: true,
            data: [],
            filtered: [],
            errors: [],
            formData: {},
            pagination: { page: 1, size: 25 },
            sort: { field: 'id', order: 'asc' },
            user: null,
            permissions: [],
            selected: [],
            history: [],
            cache: {},
            config: {},
            bulkOperation: null,
            validationErrors: [],
            token: null,
            refreshInterval: null,
            modalsOpen: {},
            lastSaved: null,
            isDirty: false,
            drafts: [],
            conflicts: [],
            syncStatus: 'synced'
        };
        this.handleInput = this.handleInput.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleSelect = this.handleSelect.bind(this);
        this.handleBulk = this.handleBulk.bind(this);
    }

    async componentDidMount() {
        const token = localStorage.getItem('token');
        if (token) {
            this.setState({ token });
            const permissions = await axios.get('/api/permissions', { headers: { Authorization: 'Bearer ' + token } });
            const user = await axios.get('/api/me', { headers: { Authorization: 'Bearer ' + token } });
            const config = await axios.get('/api/config', { headers: { Authorization: 'Bearer ' + token } });
            this.setState({ permissions: permissions.data, user: user.data, config: config.data });
            await this.loadData();
            this.setupRefresh();
        } else {
            this.props.history.push('/login');
        }
    }

    setupRefresh() {
        const interval = setInterval(async () => {
            const state = this.state;
            if (state.user && state.user.id) {
                try {
                    await axios.post('/api/refresh', {}, { headers: { Authorization: 'Bearer ' + state.token } });
                } catch (e) {
                    clearInterval(state.refreshInterval);
                    localStorage.removeItem('token');
                    this.props.history.push('/login');
                }
            }
        }, 30000);
        this.setState({ refreshInterval: interval });
    }

    handleInput(field, value, options) {
        if (options && options.validate) {
            this.validateField(field, value);
        }
        this.setState({ isDirty: true, formData: { ...this.state.formData, [field]: value } });
    }

    async loadData() {
        const { pagination, sort, token, formData, permissions } = this.state;
        const params = { ...pagination, sortBy: sort.field, sortOrder: sort.order, ...formData };
        if (permissions.includes('admin')) {
            params.includeArchived = true;
            params.includeDeleted = true;
        }
        try {
            const res = await axios.get('/api/data', { params, headers: { Authorization: 'Bearer ' + token } });
            this.setState({ data: res.data.items, filtered: res.data.items, loading: false });
        } catch (e) {
            if (e.response) {
                if (e.response.status === 401) {
                    localStorage.removeItem('token');
                    this.props.history.push('/login');
                } else if (e.response.status === 403) {
                    this.addError('权限不足');
                } else if (e.response.status === 429) {
                    this.addError('请求过于频繁，请稍后再试');
                } else {
                    this.addError('加载数据失败');
                }
            } else {
                this.addError('网络错误，请检查连接');
            }
            this.setState({ loading: false });
        }
    }

    validateField(field, value) {
        const errors = [];
        if (!value) {
            errors.push('必填字段');
        }
        if (field === 'email' && value) {
            if (!/^[.+-]+@[-]+[.-]+$/.test(value)) {
                errors.push('邮箱格式不正确');
            }
        }
        if (field === 'phone' && value) {
            if (!/^1[3-9]{9}$/.test(value)) {
                errors.push('手机号格式不正确');
            }
        }
        if (field === 'amount' && value) {
            if (Number(value) <= 0) {
                errors.push('金额必须大于0');
            }
        }
        this.setState({ validationErrors: { ...this.state.validationErrors, [field]: errors } });
        return errors.length === 0;
    }

    addError(msg) {
        const errors = this.state.errors.concat([{ id: Date.now(), msg, time: new Date() }]).slice(-10);
        this.setState({ errors });
    }

    async handleSubmit() {
        const { formData, data, isDirty, user, token, conflicts } = this.state;
        let valid = true;
        Object.keys(formData).forEach(k => {
            if (!this.validateField(k, formData[k])) valid = false;
        });
        if (!valid) {
            this.addError('表单存在错误，请检查后提交');
            return;
        }
        if (!isDirty) {
            this.addError('没有需要保存的修改');
            return;
        }
        if (conflicts && conflicts.length > 0) {
            const choice = window.confirm('存在冲突数据，确定要覆盖吗？');
            if (!choice) return;
        }
        try {
            if (formData.id) {
                await axios.put('/api/data/' + formData.id, formData, { headers: { Authorization: 'Bearer ' + token } });
            } else {
                await axios.post('/api/data', formData, { headers: { Authorization: 'Bearer ' + token } });
            }
            const newHistory = this.state.history.concat([{ action: 'save', data: formData, time: new Date(), user: user ? user.name : 'unknown' }]).slice(-100);
            this.setState({ lastSaved: new Date(), history: newHistory, isDirty: false, conflicts: [] });
            await this.loadData();
            this.addError('保存成功');
        } catch (e) {
            this.addError('保存失败: ' + (e.message || '未知错误'));
        }
    }

    handleSelect(ids, mode) {
        let selected = this.state.selected.slice();
        if (mode === 'all') {
            selected = mode ? this.state.filtered.map(i => i.id) : [];
        } else if (mode === 'single') {
            const [id] = ids;
            if (selected.includes(id)) {
                selected = selected.filter(x => x !== id);
            } else {
                selected.push(id);
            }
        } else if (mode === 'range') {
            const [start, end] = ids;
            const all = this.state.filtered.map(i => i.id);
            const startIdx = all.indexOf(start);
            const endIdx = all.indexOf(end);
            const [min, max] = startIdx < endIdx ? [startIdx, endIdx] : [endIdx, startIdx];
            for (let i = min; i <= max; i++) {
                if (!selected.includes(all[i])) selected.push(all[i]);
            }
        }
        this.setState({ selected });
    }

    async handleBulk(action, params) {
        const { selected, token, user } = this.state;
        if (!selected || selected.length === 0) {
            this.addError('请先选择数据');
            return;
        }
        const confirm = window.confirm(`确定要对${selected.length}条数据执行${action}操作吗？`);
        if (!confirm) return;
        let results = [];
        for (let i = 0; i < selected.length; i++) {
            try {
                if (action === 'delete') {
                    await axios.delete('/api/data/' + selected[i], { headers: { Authorization: 'Bearer ' + token } });
                    results.push({ id: selected[i], success: true });
                } else if (action === 'export') {
                    results.push({ id: selected[i], success: true });
                } else if (action === 'status') {
                    await axios.patch('/api/data/' + selected[i], { status: params.status }, { headers: { Authorization: 'Bearer ' + token } });
                    results.push({ id: selected[i], success: true });
                } else if (action === 'assign') {
                    await axios.patch('/api/data/' + selected[i], { owner: params.owner, updatedBy: user.id }, { headers: { Authorization: 'Bearer ' + token } });
                    results.push({ id: selected[i], success: true });
                } else if (action === 'archive') {
                    await axios.patch('/api/data/' + selected[i], { archived: true }, { headers: { Authorization: 'Bearer ' + token } });
                    results.push({ id: selected[i], success: true });
                }
            } catch (e) {
                results.push({ id: selected[i], success: false, error: e.message });
            }
        }
        const failed = results.filter(r => !r.success).length;
        if (failed > 0) {
            this.addError(`操作完成，${results.length - failed}条成功，${failed}条失败`);
        } else {
            this.addError(`操作全部成功，共${results.length}条`);
        }
        this.setState({ selected: [] });
        await this.loadData();
    }

    handlePagination(page, size) {
        this.setState({ pagination: { page, size: size || this.state.pagination.size } }, () => this.loadData());
    }

    handleSort(field) {
        let order = 'asc';
        if (this.state.sort.field === field) {
            order = this.state.sort.order === 'asc' ? 'desc' : 'asc';
        }
        this.setState({ sort: { field, order } }, () => this.loadData());
    }

    handleFilter(filters, clear) {
        if (clear) {
            this.setState({ formData: {}, filtered: this.state.data });
            return;
        }
        let filtered = this.state.data.slice();
        Object.keys(filters).forEach(k => {
            const v = filters[k];
            if (v !== undefined && v !== null && v !== '') {
                filtered = filtered.filter(item => {
                    if (typeof v === 'string') {
                        return item[k] && item[k].toString().toLowerCase().includes(v.toLowerCase());
                    }
                    return item[k] === v;
                });
            }
        });
        this.setState({ filtered });
    }
}


function legacyCalculator(items, opts, user, config) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item) {
            if (item.active) {
                if (item.verified) {
                    if (item.score > 0) {
                        let base = item.score;
                        if (opts && opts.multiplier) {
                            base = base * opts.multiplier;
                        }
                        if (user && user.level) {
                            if (user.level > 5) {
                                base = base * 1.5;
                            } else if (user.level > 2) {
                                base = base * 1.2;
                            }
                        }
                        if (config && config.tax) {
                            if (config.tax.rate) {
                                base = base * (1 + config.tax.rate);
                            }
                        }
                        total += base;
                    }
                }
            }
        }
    }
    return total;
}


export default connect(state => ({ ...state.app }))(withRouter(LegacyMonolithPage));
