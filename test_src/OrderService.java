import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import java.io.IOException;
import java.sql.Connection;
import java.sql.ResultSet;


public class OrderService {

    private Map<String, List<Order>> orderCache;
    private Connection dbConnection;
    private int maxRetries;


    public OrderService(Connection conn, int retries) {
        this.dbConnection = conn;
        this.maxRetries = retries;
        this.orderCache = new HashMap<>();
    }


    public Order processOrder(Order order, Customer customer, DiscountPolicy policy) {
        if (order == null) {
            throw new IllegalArgumentException("Order cannot be null");
        }
        if (customer == null) {
            throw new IllegalArgumentException("Customer cannot be null");
        }
        if (!customer.isActive()) {
            return null;
        }
        if (order.getItems().isEmpty()) {
            return null;
        }

        double total = 0;
        for (Item item : order.getItems()) {
            if (item.isAvailable()) {
                if (item.getPrice() > 100) {
                    if (policy.applyBulkDiscount()) {
                        total += item.getPrice() * 0.9;
                    } else {
                        total += item.getPrice();
                    }
                } else if (item.getPrice() > 50) {
                    if (customer.isPremium()) {
                        total += item.getPrice() * 0.95;
                    } else {
                        total += item.getPrice();
                    }
                } else {
                    total += item.getPrice();
                }
            } else {
                for (Item substitute : item.getSubstitutes()) {
                    if (substitute.isAvailable() && substitute.getPrice() < item.getPrice()) {
                        total += substitute.getPrice();
                        break;
                    }
                }
            }
        }

        if (total > 1000) {
            if (customer.getLoyaltyTier() == LoyaltyTier.GOLD) {
                total *= 0.85;
            } else if (customer.getLoyaltyTier() == LoyaltyTier.SILVER) {
                total *= 0.90;
            } else if (customer.getLoyaltyTier() == LoyaltyTier.BRONZE) {
                total *= 0.95;
            }
        }

        if (order.isRush() && order.getShippingAddress() != null) {
            if (order.getShippingAddress().isInternational()) {
                total += 50;
            } else {
                total += 15;
            }
        }

        order.setTotal(total);
        return order;
    }


    public List<Order> findOrdersByStatus(String status, int limit) {
        List<Order> result = new ArrayList<>();
        try {
            ResultSet rs = dbConnection.createStatement().executeQuery(
                "SELECT * FROM orders WHERE status = '" + status + "'"
            );
            while (rs.next()) {
                Order o = mapRow(rs);
                if (o != null) {
                    result.add(o);
                }
                if (result.size() >= limit) {
                    break;
                }
            }
        } catch (IOException e) {
            System.err.println("IO Error: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
        return result;
    }


    public String classifyCustomer(Customer c) {
        if (c.getTotalSpent() > 10000 && c.getOrderCount() > 50) {
            return "PLATINUM";
        } else if (c.getTotalSpent() > 5000 || c.getOrderCount() > 20) {
            return "GOLD";
        } else if (c.getTotalSpent() > 1000 && c.getOrderCount() > 5) {
            return "SILVER";
        }
        return "BRONZE";
    }


    private Order mapRow(ResultSet rs) {
        return new Order();
    }


    public static OrderService createDefault(Connection conn) {
        return new OrderService(conn, 3);
    }
}
