package com.hvac.pro.mobile;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class ApiClient {
    static final class Result {
        final int status;
        final JSONObject body;
        Result(int status, JSONObject body) { this.status = status; this.body = body; }
        boolean ok() { return status >= 200 && status < 300; }
        String message() { return body.optString("detail", body.optString("error", "Server error (" + status + ")")); }
    }

    private ApiClient() {}

    static Result get(String server, String path, String token) throws Exception {
        return request("GET", server, path, token, null);
    }

    static Result post(String server, String path, String token, JSONObject payload) throws Exception {
        return request("POST", server, path, token, payload);
    }

    private static Result request(String method, String server, String path, String token, JSONObject payload) throws Exception {
        URL url = new URL(server.replaceAll("/+$", "") + path);
        if (!BuildConfig.DEBUG && !"https".equalsIgnoreCase(url.getProtocol())) {
            throw new SecurityException("Release surumunde HTTPS gerekli.");
        }
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(20000);
        connection.setRequestProperty("Accept", "application/json");
        if (token != null && !token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
        if (payload != null) {
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            try (OutputStream output = connection.getOutputStream()) {
                output.write(payload.toString().getBytes(StandardCharsets.UTF_8));
            }
        }
        int status = connection.getResponseCode();
        InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
        StringBuilder text = new StringBuilder();
        if (stream != null) {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) text.append(line);
            }
        }
        connection.disconnect();
        return new Result(status, text.length() == 0 ? new JSONObject() : new JSONObject(text.toString()));
    }
}
