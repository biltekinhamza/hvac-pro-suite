package com.hvac.pro.mobile;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

final class DimensionPreviewView extends View {
    private final Paint imagePaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint linePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint badgePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private Bitmap bitmap;
    private JSONObject part;
    private String activeField = "";

    DimensionPreviewView(Context context) {
        super(context);
        linePaint.setStyle(Paint.Style.STROKE);
        linePaint.setStrokeCap(Paint.Cap.ROUND);
        badgePaint.setStyle(Paint.Style.FILL);
        textPaint.setTextAlign(Paint.Align.CENTER);
        textPaint.setFakeBoldText(true);
    }

    void setPart(JSONObject value) {
        part = value;
        bitmap = null;
        activeField = "";
        invalidate();
    }

    void setBitmap(Bitmap value) {
        bitmap = value;
        invalidate();
    }

    void setActiveField(String value) {
        activeField = value == null ? "" : value;
        invalidate();
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (bitmap == null || part == null) return;
        float inset = dp(10);
        float availableWidth = getWidth() - inset * 2;
        float availableHeight = getHeight() - inset * 2;
        float scale = Math.min(availableWidth / bitmap.getWidth(), availableHeight / bitmap.getHeight());
        float width = bitmap.getWidth() * scale;
        float height = bitmap.getHeight() * scale;
        RectF imageRect = new RectF((getWidth() - width) / 2, (getHeight() - height) / 2,
            (getWidth() + width) / 2, (getHeight() + height) / 2);
        canvas.drawBitmap(bitmap, null, imageRect, imagePaint);
        drawMarkers(canvas, imageRect);
    }

    private void drawMarkers(Canvas canvas, RectF imageRect) {
        JSONArray markers = part.optJSONArray("dimension_markers");
        if (markers == null) return;
        for (int i = 0; i < markers.length(); i++) {
            JSONObject marker = markers.optJSONObject(i);
            if (marker == null) continue;
            boolean active = marker.optString("field").equals(activeField);
            int color = active ? Color.rgb(234, 88, 12) : Color.rgb(7, 89, 133);
            linePaint.setColor(color);
            linePaint.setStrokeWidth(dp(active ? 2.5f : 1.4f));
            linePaint.setAlpha(active || activeField.isEmpty() ? 255 : 65);
            JSONArray segments = marker.optJSONArray("segments");
            if (segments == null || segments.length() == 0) {
                drawLine(canvas, imageRect, marker.optJSONArray("line"));
            } else {
                for (int j = 0; j < segments.length(); j++) drawLine(canvas, imageRect, segments.optJSONArray(j));
            }
            drawBadge(canvas, imageRect, marker, color, active);
        }
    }

    private void drawLine(Canvas canvas, RectF rect, JSONArray line) {
        if (line == null || line.length() < 4) return;
        canvas.drawLine(mapX(rect, line.optDouble(0)), mapY(rect, line.optDouble(1)),
            mapX(rect, line.optDouble(2)), mapY(rect, line.optDouble(3)), linePaint);
    }

    private void drawBadge(Canvas canvas, RectF rect, JSONObject marker, int color, boolean active) {
        JSONArray label = marker.optJSONArray("label");
        if (label == null || label.length() < 2) return;
        String symbol = marker.optString("symbol", "?");
        float x = mapX(rect, label.optDouble(0));
        float y = mapY(rect, label.optDouble(1));
        textPaint.setTextSize(dp(active ? 12 : 11));
        textPaint.setColor(active ? Color.rgb(154, 52, 18) : color);
        float horizontal = textPaint.measureText(symbol) / 2 + dp(8);
        RectF badge = new RectF(x - horizontal, y - dp(13), x + horizontal, y + dp(13));
        badgePaint.setColor(active ? Color.rgb(255, 247, 237) : Color.WHITE);
        badgePaint.setAlpha(active || activeField.isEmpty() ? 235 : 90);
        canvas.drawRoundRect(badge, dp(13), dp(13), badgePaint);
        textPaint.setAlpha(active || activeField.isEmpty() ? 255 : 80);
        canvas.drawText(symbol, x, y - (textPaint.ascent() + textPaint.descent()) / 2, textPaint);
    }

    private float mapX(RectF rect, double value) { return rect.left + (float) value * rect.width() / 100f; }
    private float mapY(RectF rect, double value) { return rect.top + (float) value * rect.height() / 100f; }
    private float dp(float value) { return value * getResources().getDisplayMetrics().density; }
}
