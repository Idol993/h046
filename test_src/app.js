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
