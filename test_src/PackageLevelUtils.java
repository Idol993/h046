package com.example.internal;

import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;


class PackageLevelUtils {

    private Map<String, String> cache;
    private String mode;
    private int maxSize;


    PackageLevelUtils() {
        this.cache = new HashMap<>();
        this.mode = "DEFAULT";
        this.maxSize = 100;
    }


    PackageLevelUtils(String customMode, int size) {
        this.cache = new HashMap<>();
        this.mode = customMode;
        this.maxSize = size;
    }


    public String classifyCustomerType(Customer customer) {
        String type = customer.getOrders().size() > 50
            ? "PLATINUM"
            : customer.getOrders().size() > 20
                ? "GOLD"
                : customer.getOrders().size() > 10
                    ? "SILVER"
                    : customer.getOrders().size() > 3
                        ? "BRONZE"
                        : "BASIC";

        String tier = customer.isVerified()
            ? customer.hasPremiumMembership()
                ? "ELITE"
                : "STANDARD"
            : "PENDING";

        return type + "-" + tier;
    }


    public List<String> resolveStatusCodes(Order order) {
        List<String> codes = new ArrayList<>();
        switch (order.getState()) {
            case CREATED:
                codes.add("NEW");
                codes.add("100");
                break;
            case PAID:
                codes.add("CONFIRMED");
                codes.add("200");
                break;
            case SHIPPED:
                codes.add("IN_TRANSIT");
                codes.add("300");
                break;
            case DELIVERED:
                codes.add("COMPLETED");
                codes.add("400");
                break;
            case CANCELLED:
                codes.add("CANCELLED");
                codes.add("500");
                break;
            case REFUNDED:
                codes.add("REFUND");
                codes.add("600");
                break;
            default:
                codes.add("UNKNOWN");
                codes.add("0");
                break;
        }

        for (int i = 0; i < order.getItems().size(); i++) {
            String status;
            switch (order.getItems().get(i).getCondition()) {
                case NEW:
                    status = "SEALED";
                    break;
                case USED:
                    status = "OPENED";
                    break;
                case DAMAGED:
                    status = "DEFECT";
                    break;
                default:
                    status = "NA";
                    break;
            }
            codes.add(status);
        }

        return codes;
    }


    public int calculateRiskScore(Customer customer, Order order) {
        int score = 0;
        if (customer == null || order == null) {
            String safe = order != null
                ? order.getId()
                : customer != null
                    ? customer.getId()
                    : "safe";
            return -1;
        }

        if (customer.getAge() < 18) {
            score += 10;
        } else if (customer.getAge() < 21) {
            score += 5;
        }

        if (order.getTotal() > 10000 && !customer.isVerified()) {
            score += 50;
        } else if (order.getTotal() > 5000 && order.isInternational()) {
            score += 30;
        }

        try {
            if (order.isHighValue()) {
                for (int i = 0; i < customer.getAddresses().size(); i++) {
                    if (customer.getAddresses().get(i).isNew()) {
                        if (customer.getAddresses().size() > 5) {
                            score += 20;
                        } else if (order.getTotal() > 2000) {
                            score += 10;
                        }
                    }
                }
            }
        } catch (Exception e) {
            score += 100;
        }

        return score;
    }


    String stringBraceSafe() {
        String template = "{ \"name\": \"{name}\", \"count\": {count} }";
        String json = "{ items: [ {id: 1}, {id: 2} ] }";
        return template + json;
    }
}
