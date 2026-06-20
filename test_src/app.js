import React, { useState, useEffect } from 'react';
import axios from 'axios';
import lodash from 'lodash';
import moment from 'moment';
import { Button, Input, Form, Modal, Table, Card, Alert } from 'antd';
import { connect } from 'react-redux';
import { Route, Link, Switch, Redirect } from 'react-router-dom';


function processUserData(users, filter, options) {
    let result = [];
    for (let i = 0; i < users.length; i++) {
        const user = users[i];
        if (user.active) {
            if (user.age > 18) {
                if (filter.country) {
                    if (user.country === filter.country) {
                        if (user.score > filter.minScore) {
                            for (let j = 0; j < user.orders.length; j++) {
                                const order = user.orders[j];
                                if (order.status === 'completed') {
                                    if (order.total > 100) {
                                        if (options.includeDetails) {
                                            for (let k = 0; k < order.items.length; k++) {
                                                if (k > 10) break;
                                            }
                                        }
                                    } else if (order.total > 50) {
                                        result.push(user);
                                    }
                                } else if (order.status === 'pending') {
                                    if (order.createdAt < filter.beforeDate) {
                                        result.push(user);
                                    }
                                }
                            }
                        }
                    } else if (user.country === 'US' || user.country === 'UK') {
                        if (user.score > 80) {
                            result.push(user);
                        }
                    }
                }
            } else if (user.age > 13) {
                if (user.score > 90) {
                    result.push(user);
                }
            }
        }
    }
    return result;
}


function simpleAdd(a, b) {
    return a + b;
}


export function exportedHelper(data) {
    if (data && data.length > 0) {
        for (let item of data) {
            if (item.active && item.verified) {
                processItem(item);
            }
        }
    }
    return data;
}


export default function mainEntry(config) {
    if (config.debug) {
        console.log('debug mode');
    }
    return config;
}


const arrowSum = (a, b) => a + b;


const arrowComplex = (items) => {
    let result = 0;
    for (let i = 0; i < items.length; i++) {
        if (items[i].valid) {
            if (items[i].score > 50) {
                result += items[i].score;
            } else if (items[i].score > 20) {
                result += items[i].score / 2;
            }
        }
    }
    return result;
};


const asyncFetchData = async (url) => {
    try {
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                return data.result;
            } else {
                throw new Error('API error');
            }
        }
    } catch (err) {
        console.error(err);
    }
};


const objMethods = {
    validate: function(input) {
        if (!input) return false;
        if (input.length > 100) return false;
        if (input.length < 3) return false;
        return true;
    },

    transform: function(data) {
        let result = [];
        for (let key in data) {
            if (data.hasOwnProperty(key) && data[key] !== null) {
                result.push({ key: key, value: data[key] });
            }
        }
        return result;
    }
};


class UserService {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.cache = {};
    }

    getUser(id) {
        if (this.cache[id]) {
            return this.cache[id];
        }
        if (id > 0 && id < 10000) {
            return this.fetchUser(id);
        }
        return null;
    }

    async fetchUser(id) {
        try {
            const resp = await fetch(this.apiUrl + '/users/' + id);
            if (resp.ok) {
                const user = await resp.json();
                if (user && user.active) {
                    this.cache[id] = user;
                    return user;
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

    static createDefault() {
        return new UserService('https://api.example.com');
    }
}
