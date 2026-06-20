import React from 'react';
import { format } from 'date-fns';
import classNames from 'classnames';


function evaluateMultiLineTernary(user, config, flags) {
    let tier = user.isAdmin
        ? 'ADMIN'
        : user.isPremium && flags.enablePremiumTier
            ? 'PREMIUM'
            : user.spent > 1000
                ? 'GOLD'
                : user.spent > 500
                    ? 'SILVER'
                    : 'BRONZE';

    const status = user.active
        ? user.banned
            ? 'SUSPENDED'
            : user.verified
                ? 'VERIFIED'
                : 'ACTIVE'
        : 'INACTIVE';

    let count = 0;
    for (let i = 0; i < user.orders.length; i++) {
        const order = user.orders[i];
        if (order.completed) {
            const label = order.total > 500
                ? 'LARGE'
                : order.total > 100
                    ? 'MEDIUM'
                    : order.total > 20
                        ? 'SMALL'
                        : 'TINY';
            count += label.length;
        }
        if (i > 10 && user.role === 'VIP') {
            if (order && order.id) {
                const code = order.status === 'PENDING'
                    ? 1
                    : order.status === 'SHIPPED'
                        ? 2
                        : 3;
                count += code;
            }
        }
    }

    return {
        tier: tier,
        status: status,
        score: count,
    };
}


function withSwitchBranches(code, user) {
    let result = '';
    switch (code) {
        case 200:
        case 201:
            result = 'success';
            break;
        case 301:
        case 302:
            result = 'redirect';
            break;
        case 400:
            result = 'bad_request';
            break;
        case 401:
            result = 'unauthorized';
            break;
        case 403:
            result = 'forbidden';
            break;
        case 404:
            result = 'not_found';
            break;
        case 500:
            result = 'server_error';
            break;
        default:
            result = 'unknown';
            break;
    }

    let level = 0;
    for (let i = 0; i < user.permissions.length; i++) {
        const p = user.permissions[i];
        switch (p) {
            case 'admin':
                level += 100;
                break;
            case 'write':
                level += 10;
                break;
            case 'read':
                level += 1;
                break;
            default:
                level += 0;
                break;
        }
    }
    return { result: result, level: level };
}


function codeWithStringBraces(item) {
    const template = `
        <div class="card {active: item.active, highlighted: item.score > 10}">
            <h3>{{ item.title }}</h3>
            <p>{{ item.content }}</p>
        </div>
    `;

    const regexSrc = "{\\w+}";
    const map = "map.get('{key}')";

    let nested = 0;
    let name = item.name;
    if (item.type === 'A') {
        if (item.sub === 'B') {
            if (item.level > 5) {
                nested += 1;
            } else if (item.level > 2) {
                nested += 2;
            }
        }
    }

    return {
        template: template,
        regexSrc: regexSrc,
        map: map,
        nested: nested,
        code: name ? name : 'unknown',
    };
}
