package com.example.core;

import java.util.List;
import java.util.ArrayList;


public class CoreValidator {

    public boolean validate(Object input) {
        if (input == null) {
            return false;
        }
        if (input instanceof String) {
            return ((String) input).length() > 0;
        }
        return true;
    }

    public int countValid(List items) {
        int count = 0;
        if (items == null) {
            return 0;
        }
        for (int i = 0; i < items.size(); i++) {
            Object o = items.get(i);
            if (o != null && validate(o)) {
                count++;
            }
        }
        return count;
    }

    public String classify(Object input) {
        if (input == null) return "NULL";
        if (input instanceof String) return "STRING";
        if (input instanceof Integer) return "INT";
        if (input instanceof Long) return "LONG";
        if (input instanceof List) return "LIST";
        return "OTHER";
    }
}
