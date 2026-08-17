package com.hvac.pro.mobile;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

final class QueueDb extends SQLiteOpenHelper {
    static final class Pending {
        final long id;
        final String operationId;
        final String type;
        final String payload;
        final int attempts;
        Pending(long id, String operationId, String type, String payload, int attempts) {
            this.id = id; this.operationId = operationId; this.type = type; this.payload = payload; this.attempts = attempts;
        }
    }

    QueueDb(Context context) { super(context, "hvac_mobile.db", null, 2); }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE catalog(profile TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)");
        db.execSQL("CREATE TABLE draft(profile TEXT NOT NULL, local_id TEXT NOT NULL, customer TEXT NOT NULL DEFAULT '', customer_phone TEXT NOT NULL DEFAULT '', profit REAL NOT NULL DEFAULT 0, shipping REAL NOT NULL DEFAULT 0, PRIMARY KEY(profile, local_id))");
        db.execSQL("CREATE TABLE draft_item(id INTEGER PRIMARY KEY AUTOINCREMENT, profile TEXT NOT NULL, local_id TEXT NOT NULL, part_code TEXT NOT NULL, part_title TEXT NOT NULL, inputs TEXT NOT NULL, quantity INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE pending(id INTEGER PRIMARY KEY AUTOINCREMENT, profile TEXT NOT NULL, operation_id TEXT NOT NULL UNIQUE, operation_type TEXT NOT NULL, payload TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'pending', last_error TEXT)");
    }

    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        if (oldVersion < 2) db.execSQL("ALTER TABLE draft ADD COLUMN customer_phone TEXT NOT NULL DEFAULT ''");
    }

    void saveCatalog(String profile, JSONObject payload) {
        ContentValues values = new ContentValues();
        values.put("profile", profile); values.put("payload", payload.toString());
        getWritableDatabase().insertWithOnConflict("catalog", null, values, SQLiteDatabase.CONFLICT_REPLACE);
    }

    JSONObject catalog(String profile) throws Exception {
        try (Cursor cursor = getReadableDatabase().query("catalog", new String[]{"payload"}, "profile=?", new String[]{profile}, null, null, null)) {
            return cursor.moveToFirst() ? new JSONObject(cursor.getString(0)) : new JSONObject().put("parts", new JSONArray());
        }
    }

    void saveDraftHeader(String profile, String localId, String customer, String customerPhone, double profit, double shipping) {
        ContentValues values = new ContentValues();
        values.put("profile", profile); values.put("local_id", localId); values.put("customer", customer);
        values.put("customer_phone", customerPhone);
        values.put("profit", profit); values.put("shipping", shipping);
        getWritableDatabase().insertWithOnConflict("draft", null, values, SQLiteDatabase.CONFLICT_REPLACE);
    }

    JSONObject draftHeader(String profile, String localId) throws Exception {
        try (Cursor cursor = getReadableDatabase().query("draft", new String[]{"customer", "customer_phone", "profit", "shipping"}, "profile=? AND local_id=?", new String[]{profile, localId}, null, null, null)) {
            if (!cursor.moveToFirst()) return new JSONObject();
            return new JSONObject().put("customer", cursor.getString(0)).put("customer_phone", cursor.getString(1)).put("profit", cursor.getDouble(2)).put("shipping", cursor.getDouble(3));
        }
    }

    void addItem(String profile, String localId, String code, String title, JSONObject inputs, int quantity) {
        ContentValues values = new ContentValues();
        values.put("profile", profile); values.put("local_id", localId); values.put("part_code", code);
        values.put("part_title", title); values.put("inputs", inputs.toString()); values.put("quantity", quantity);
        getWritableDatabase().insertOrThrow("draft_item", null, values);
    }

    JSONArray items(String profile, String localId) throws Exception {
        JSONArray result = new JSONArray();
        try (Cursor cursor = getReadableDatabase().query("draft_item", new String[]{"id", "part_code", "part_title", "inputs", "quantity"}, "profile=? AND local_id=?", new String[]{profile, localId}, null, null, "id")) {
            while (cursor.moveToNext()) {
                result.put(new JSONObject().put("row_id", cursor.getLong(0)).put("part_code", cursor.getString(1))
                    .put("part_title", cursor.getString(2)).put("inputs", new JSONObject(cursor.getString(3))).put("quantity", cursor.getInt(4)));
            }
        }
        return result;
    }

    void removeItem(String profile, long id) {
        getWritableDatabase().delete("draft_item", "profile=? AND id=?", new String[]{profile, String.valueOf(id)});
    }

    void updateItem(String profile, long id, JSONObject inputs, int quantity) {
        ContentValues values = new ContentValues();
        values.put("inputs", inputs.toString());
        values.put("quantity", quantity);
        getWritableDatabase().update("draft_item", values, "profile=? AND id=?", new String[]{profile, String.valueOf(id)});
    }

    JSONObject operationPayload(String profile, String localId, String operationId, String type) throws Exception {
        try (Cursor cursor = getReadableDatabase().query("draft", new String[]{"customer", "customer_phone", "profit", "shipping"}, "profile=? AND local_id=?", new String[]{profile, localId}, null, null, null)) {
            if (!cursor.moveToFirst()) throw new IllegalStateException("Taslak bulunamadi.");
            JSONArray source = items(profile, localId);
            JSONArray cleanItems = new JSONArray();
            for (int i = 0; i < source.length(); i++) {
                JSONObject item = source.getJSONObject(i);
                cleanItems.put(new JSONObject().put("part_code", item.getString("part_code"))
                    .put("inputs", item.getJSONObject("inputs")).put("quantity", item.getInt("quantity")));
            }
            JSONObject draft = new JSONObject().put("local_id", localId).put("customer_name", cursor.getString(0))
                .put("customer_phone", cursor.getString(1)).put("profit_rate", cursor.getDouble(2)).put("shipping_amount", cursor.getDouble(3)).put("items", cleanItems);
            return new JSONObject().put("operation_id", operationId).put("type", type).put("draft", draft);
        }
    }

    void enqueue(String profile, String operationId, String type, JSONObject payload) {
        ContentValues values = new ContentValues();
        values.put("profile", profile); values.put("operation_id", operationId); values.put("operation_type", type); values.put("payload", payload.toString());
        getWritableDatabase().insertOrThrow("pending", null, values);
    }

    List<Pending> pending(String profile) {
        List<Pending> result = new ArrayList<>();
        try (Cursor cursor = getReadableDatabase().query("pending", new String[]{"id", "operation_id", "operation_type", "payload", "attempts"}, "profile=? AND state='pending'", new String[]{profile}, null, null, "id")) {
            while (cursor.moveToNext()) result.add(new Pending(cursor.getLong(0), cursor.getString(1), cursor.getString(2), cursor.getString(3), cursor.getInt(4)));
        }
        return result;
    }

    void complete(long id) { getWritableDatabase().delete("pending", "id=?", new String[]{String.valueOf(id)}); }

    void fail(long id, String error) {
        ContentValues values = new ContentValues(); values.put("state", "failed"); values.put("last_error", error);
        getWritableDatabase().update("pending", values, "id=?", new String[]{String.valueOf(id)});
    }

    void retry(long id, int attempts, String error) {
        ContentValues values = new ContentValues(); values.put("attempts", attempts); values.put("last_error", error);
        getWritableDatabase().update("pending", values, "id=?", new String[]{String.valueOf(id)});
    }

    int count(String profile, String state) {
        try (Cursor cursor = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM pending WHERE profile=? AND state=?", new String[]{profile, state})) {
            cursor.moveToFirst(); return cursor.getInt(0);
        }
    }
}
