package com.hvac.pro.mobile;

import android.app.Activity;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int INK = Color.rgb(23, 33, 43);
    private static final int ORANGE = Color.rgb(217, 119, 6);
    private static final int GREEN = Color.rgb(22, 124, 78);
    private static final int MUTED = Color.rgb(98, 108, 118);
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable queueTicker = new Runnable() {
        @Override public void run() { refreshQueueState(); handler.postDelayed(this, 2500); }
    };
    private final Map<String, EditText> partInputs = new LinkedHashMap<>();
    private SharedPreferences prefs;
    private QueueDb db;
    private TextView queueState;
    private LinearLayout itemList;
    private LinearLayout fields;
    private EditText customer;
    private EditText customerPhone;
    private EditText quantity;
    private Spinner sheetThickness;
    private DimensionPreviewView partPreview;
    private JSONArray parts = new JSONArray();
    private JSONObject selectedPart;
    private String profile;
    private String draftId;
    private Button cartButton;
    private boolean cartOpen;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("connection", MODE_PRIVATE);
        db = new QueueDb(this);
        if (prefs.getString("token", "").isEmpty()) showActivation(); else showDraft();
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private TextView label(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(color);
        view.setTypeface(Typeface.DEFAULT, bold ? Typeface.BOLD : Typeface.NORMAL);
        return view;
    }

    private GradientDrawable background(int color, int radius, int stroke) {
        GradientDrawable result = new GradientDrawable();
        result.setColor(color); result.setCornerRadius(dp(radius));
        if (stroke != Color.TRANSPARENT) result.setStroke(dp(1), stroke);
        return result;
    }

    private EditText input(String hint) {
        EditText view = new EditText(this);
        view.setHint(hint); view.setTextSize(15); view.setSingleLine(true); view.setPadding(dp(13), 0, dp(13), 0);
        view.setBackground(background(Color.WHITE, 9, Color.rgb(205, 198, 185)));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        params.bottomMargin = dp(10); view.setLayoutParams(params);
        return view;
    }

    private Button button(String text, int color) {
        Button result = new Button(this);
        result.setText(text); result.setTextColor(Color.WHITE); result.setTextSize(14); result.setAllCaps(false);
        result.setTypeface(Typeface.DEFAULT, Typeface.BOLD); result.setBackground(background(color, 9, Color.TRANSPARENT));
        return result;
    }

    private void addLabeled(LinearLayout parent, String title, View control) {
        TextView fieldLabel = label(title, 12, MUTED, true);
        fieldLabel.setPadding(dp(2), dp(8), 0, dp(5));
        parent.addView(fieldLabel);
        parent.addView(control);
    }

    private void showActivation() {
        handler.removeCallbacks(queueTicker);
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(24), dp(54), dp(24), dp(24));
        root.setBackgroundColor(Color.rgb(245, 241, 232)); scroll.addView(root);
        root.addView(label("HVAC PRO / SAHA", 12, ORANGE, true));
        TextView title = label("Teklif taslaklari,\ncevrimdisi da.", 31, INK, true);
        title.setPadding(0, dp(8), 0, dp(12)); root.addView(title);
        TextView description = label("Sirket sunucusunu bir kez aktive edin. Taslaklar cihazda kalir ve baglanti geldiginde sunucuda hesaplanir.", 15, MUTED, false);
        description.setPadding(0, 0, 0, dp(24)); root.addView(description);
        EditText server = input("https://firma.example.com");
        server.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        if (BuildConfig.DEBUG) server.setText("http://10.0.2.2:8010");
        EditText code = input("Aktivasyon kodu");
        EditText name = input("Cihaz adi"); name.setText(Build.MANUFACTURER + " " + Build.MODEL);
        root.addView(server); root.addView(code); root.addView(name);
        Button activate = button("Cihazi aktive et", ORANGE);
        activate.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56))); root.addView(activate);
        TextView secure = label("Release surumu yalniz HTTPS kabul eder.", 12, MUTED, false);
        secure.setGravity(Gravity.CENTER); secure.setPadding(0, dp(14), 0, 0); root.addView(secure);
        setContentView(scroll);

        activate.setOnClickListener(v -> {
            String serverValue = server.getText().toString().trim().replaceAll("/+$", "");
            if (code.getText().toString().trim().isEmpty() || (!BuildConfig.DEBUG && !serverValue.startsWith("https://"))) {
                toast("HTTPS adresi ve aktivasyon kodu gerekli."); return;
            }
            activate.setEnabled(false);
            executor.execute(() -> {
                try {
                    JSONObject body = new JSONObject().put("activation_code", code.getText().toString().trim())
                        .put("device_id", Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID))
                        .put("device_name", name.getText().toString().trim());
                    ApiClient.Result result = ApiClient.post(serverValue, "/api/v1/activate", null, body);
                    if (!result.ok()) throw new Exception(result.message());
                    String tenant = result.body.getString("tenant_id");
                    String newProfile = profileKey(serverValue, tenant);
                    prefs.edit().putString("server", serverValue).putString("token", result.body.getString("token"))
                        .putString("tenant", tenant).putString("profile", newProfile)
                        .putString("company", result.body.optString("company_name", "HVAC Pro Suite")).apply();
                    runOnUiThread(this::showDraft);
                } catch (Exception error) {
                    runOnUiThread(() -> { activate.setEnabled(true); toast(error.getMessage()); });
                }
            });
        });
    }

    private void showDraft() {
        handler.removeCallbacks(queueTicker);
        cartOpen = false;
        profile = prefs.getString("profile", "");
        String key = "draft_" + profile;
        draftId = prefs.getString(key, "");
        if (draftId.isEmpty()) { draftId = UUID.randomUUID().toString(); prefs.edit().putString(key, draftId).apply(); }

        LinearLayout screen = new LinearLayout(this); screen.setOrientation(LinearLayout.VERTICAL); screen.setBackgroundColor(Color.rgb(245, 241, 232));
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(18), dp(12), dp(18), dp(12)); header.setBackgroundColor(INK);
        LinearLayout brand = new LinearLayout(this); brand.setOrientation(LinearLayout.VERTICAL);
        brand.addView(label("HVAC Mobil", 20, Color.WHITE, true)); brand.addView(label(prefs.getString("company", "HVAC Pro Suite"), 11, Color.rgb(205, 213, 219), false));
        header.addView(brand, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        Button disconnect = button("Sunucu", Color.rgb(58, 70, 82)); header.addView(disconnect, new LinearLayout.LayoutParams(dp(82), dp(42))); screen.addView(header);

        ScrollView scroll = new ScrollView(this); LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL); content.setPadding(dp(16), dp(16), dp(16), dp(32)); scroll.addView(content);
        queueState = label("", 13, MUTED, true); queueState.setPadding(0, 0, 0, dp(12)); content.addView(queueState);
        content.addView(label("PARCA KATALOGU", 12, ORANGE, true));
        Spinner spinner = new Spinner(this); spinner.setBackground(background(Color.WHITE, 9, Color.rgb(205, 198, 185)));
        LinearLayout.LayoutParams spinnerParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(54)); spinnerParams.bottomMargin = dp(10); content.addView(spinner, spinnerParams);
        partPreview = new DimensionPreviewView(this);
        partPreview.setBackground(background(Color.WHITE, 9, Color.rgb(218, 211, 199)));
        LinearLayout.LayoutParams imageParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(240)); imageParams.bottomMargin = dp(12); content.addView(partPreview, imageParams);
        fields = new LinearLayout(this); fields.setOrientation(LinearLayout.VERTICAL); content.addView(fields);
        sheetThickness = new Spinner(this); sheetThickness.setBackground(background(Color.WHITE, 9, Color.rgb(205, 198, 185)));
        quantity = numberInput("Adet", "1");
        addLabeled(content, "SAC KALINLIGI", sheetThickness);
        addLabeled(content, "ADET", quantity);
        Button add = button("Sepete Ekle", ORANGE); content.addView(add, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));
        cartButton = button("Sepete Git", GREEN);
        LinearLayout.LayoutParams cartParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)); cartParams.topMargin = dp(12); content.addView(cartButton, cartParams);
        screen.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1)); setContentView(screen);

        disconnect.setOnClickListener(v -> { prefs.edit().remove("token").remove("server").remove("profile").remove("tenant").apply(); showActivation(); });
        add.setOnClickListener(v -> addDraftItem()); cartButton.setOnClickListener(v -> showCart());
        loadCatalog(spinner); refreshCartButton(); refreshQueueState(); handler.post(queueTicker); refreshCatalog(spinner);
    }

    private void showCart() {
        handler.removeCallbacks(queueTicker);
        cartOpen = true;
        LinearLayout screen = new LinearLayout(this); screen.setOrientation(LinearLayout.VERTICAL); screen.setBackgroundColor(Color.rgb(245, 241, 232));
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(14), dp(12), dp(18), dp(12)); header.setBackgroundColor(INK);
        Button back = button("Urunler", Color.rgb(58, 70, 82)); header.addView(back, new LinearLayout.LayoutParams(dp(92), dp(42)));
        TextView title = label("Sepetim", 21, Color.WHITE, true); title.setPadding(dp(14), 0, 0, 0); header.addView(title); screen.addView(header);

        ScrollView scroll = new ScrollView(this); LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL); content.setPadding(dp(16), dp(16), dp(16), dp(32)); scroll.addView(content);
        queueState = label("", 13, MUTED, true); queueState.setPadding(0, 0, 0, dp(10)); content.addView(queueState);
        customer = input("Musteri / firma adi");
        customerPhone = input("05xx xxx xx xx");
        customerPhone.setInputType(InputType.TYPE_CLASS_PHONE);
        restoreHeader();
        addLabeled(content, "MUSTERI / FIRMA ADI", customer);
        addLabeled(content, "TELEFON", customerPhone);
        TextView itemTitle = label("SEPET KALEMLERI", 12, ORANGE, true); itemTitle.setPadding(0, dp(14), 0, dp(8)); content.addView(itemTitle);
        itemList = new LinearLayout(this); itemList.setOrientation(LinearLayout.VERTICAL); content.addView(itemList);
        Button submit = button("Teklif Iste", GREEN);
        LinearLayout.LayoutParams submitParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)); submitParams.topMargin = dp(14); content.addView(submit, submitParams);
        screen.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1)); setContentView(screen);
        back.setOnClickListener(v -> showDraft()); submit.setOnClickListener(v -> queueOperation("submit_quote"));
        renderCartItems(); refreshQueueState(); handler.post(queueTicker);
    }

    private EditText numberInput(String hint, String value) {
        EditText result = input(hint); result.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL); result.setText(value); return result;
    }

    private void loadCatalog(Spinner spinner) {
        try {
            parts = db.catalog(profile).optJSONArray("parts");
            if (parts == null) parts = new JSONArray();
            loadSheetOptions(db.catalog(profile).optJSONArray("material_options"));
            List<String> names = new ArrayList<>();
            for (int i = 0; i < parts.length(); i++) names.add(parts.getJSONObject(i).getString("title"));
            spinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, names));
            spinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    try { selectedPart = parts.getJSONObject(position); renderPartFields(); loadPartImage(); } catch (Exception error) { toast("Katalog okunamadi."); }
                }
                @Override public void onNothingSelected(AdapterView<?> parent) { selectedPart = null; }
            });
        } catch (Exception error) { toast("Yerel katalog okunamadi."); }
    }

    private void loadSheetOptions(JSONArray materials) throws Exception {
        List<String> values = sheetOptionValues(materials);
        sheetThickness.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values));
        int defaultIndex = values.indexOf("0.60");
        if (defaultIndex >= 0) sheetThickness.setSelection(defaultIndex);
    }

    private List<String> sheetOptionValues(JSONArray materials) throws Exception {
        List<String> values = new ArrayList<>();
        if (materials != null) {
            for (int i = 0; i < materials.length(); i++) {
                JSONObject material = materials.getJSONObject(i);
                if (!"SAC".equalsIgnoreCase(material.optString("name"))) continue;
                String value = material.optString("option_name").trim().split("\\s+")[0].replace(',', '.');
                if (!value.isEmpty() && !values.contains(value)) values.add(value);
            }
        }
        if (values.isEmpty()) { values.add("0.50"); values.add("0.60"); values.add("0.65"); values.add("0.70"); values.add("0.80"); }
        return values;
    }

    private void loadPartImage() {
        partPreview.setPart(selectedPart);
        String path = selectedPart == null ? "" : selectedPart.optString("image");
        if (path.isEmpty()) return;
        String partCode = selectedPart.optString("code");
        executor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(prefs.getString("server", "").replaceAll("/+$", "") + "/static/parcalar/" + path);
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(10000); connection.setReadTimeout(15000);
                Bitmap bitmap = BitmapFactory.decodeStream(connection.getInputStream());
                if (bitmap != null) runOnUiThread(() -> {
                    if (selectedPart != null && partCode.equals(selectedPart.optString("code"))) partPreview.setBitmap(bitmap);
                });
            } catch (Exception ignored) {
                // The form remains usable when an image is unavailable offline.
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private void refreshCatalog(Spinner spinner) {
        executor.execute(() -> {
            try {
                ApiClient.Result result = ApiClient.get(prefs.getString("server", ""), "/api/v1/catalog", prefs.getString("token", ""));
                if (!result.ok()) throw new Exception(result.message());
                db.saveCatalog(profile, result.body);
                runOnUiThread(() -> loadCatalog(spinner));
            } catch (Exception ignored) { runOnUiThread(() -> toast("Cevrimdisi katalog kullaniliyor.")); }
        });
    }

    private void renderPartFields() throws Exception {
        fields.removeAllViews(); partInputs.clear();
        JSONArray definitions = selectedPart.getJSONArray("fields");
        for (int i = 0; i < definitions.length(); i++) {
            JSONObject definition = definitions.getJSONObject(i); EditText value = numberInput(definition.getString("label"), "");
            String fieldName = definition.getString("name");
            value.setOnFocusChangeListener((view, hasFocus) -> { if (hasFocus) partPreview.setActiveField(fieldName); });
            partInputs.put(definition.getString("name"), value); fields.addView(value);
        }
    }

    private void addDraftItem() {
        if (selectedPart == null) { toast("Once katalogdan parca secin."); return; }
        try {
            JSONObject inputs = new JSONObject();
            for (Map.Entry<String, EditText> entry : partInputs.entrySet()) {
                String value = entry.getValue().getText().toString().trim();
                if (value.isEmpty()) throw new IllegalArgumentException("Tum olculeri girin.");
                inputs.put(entry.getKey(), value.replace(',', '.'));
            }
            inputs.put("sac_kalinlik_mm", String.valueOf(sheetThickness.getSelectedItem()));
            int count = Math.max(1, Integer.parseInt(quantity.getText().toString()));
            db.addItem(profile, draftId, selectedPart.getString("code"), selectedPart.getString("title"), inputs, count);
            refreshCartButton(); toast("Parca sepete eklendi.");
        } catch (Exception error) { toast(error.getMessage()); }
    }

    private void refreshCartButton() {
        if (cartButton == null) return;
        try {
            int count = db.items(profile, draftId).length();
            cartButton.setText("Sepete Git (" + count + ")");
        } catch (Exception ignored) { cartButton.setText("Sepete Git"); }
    }

    private void renderCartItems() {
        if (itemList == null) return;
        itemList.removeAllViews();
        try {
            JSONArray values = db.items(profile, draftId);
            for (int i = 0; i < values.length(); i++) {
                JSONObject item = values.getJSONObject(i);
                final long id = item.getLong("row_id");
                final String partCode = item.getString("part_code");
                JSONObject originalInputs = item.getJSONObject("inputs");
                int itemCount = item.getInt("quantity");

                LinearLayout card = new LinearLayout(this); card.setOrientation(LinearLayout.VERTICAL);
                card.setBackground(background(Color.WHITE, 12, Color.rgb(218, 211, 199)));
                LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); cardParams.bottomMargin = dp(12); card.setLayoutParams(cardParams);

                LinearLayout headerRow = new LinearLayout(this); headerRow.setGravity(Gravity.CENTER_VERTICAL); headerRow.setPadding(dp(14), dp(10), dp(14), dp(10));
                LinearLayout headerText = new LinearLayout(this); headerText.setOrientation(LinearLayout.VERTICAL);
                headerText.addView(label(item.getString("part_title"), 17, INK, true));
                headerText.addView(label(itemSummary(partCode, originalInputs, itemCount), 12, MUTED, false));
                headerRow.addView(headerText, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                TextView expandIcon = label("+", 22, ORANGE, true); headerRow.addView(expandIcon);
                card.addView(headerRow);

                LinearLayout detail = new LinearLayout(this); detail.setOrientation(LinearLayout.VERTICAL); detail.setPadding(dp(14), 0, dp(14), dp(14));
                detail.setVisibility(View.GONE);
                Map<String, View> editors = new LinkedHashMap<>();
                Iterator<String> keys = originalInputs.keys();
                while (keys.hasNext()) {
                    String key = keys.next();
                    View editor;
                    if ("sac_kalinlik_mm".equals(key)) {
                        Spinner sheetEditor = new Spinner(this);
                        sheetEditor.setBackground(background(Color.WHITE, 9, Color.rgb(205, 198, 185)));
                        List<String> options = sheetOptionValues(db.catalog(profile).optJSONArray("material_options"));
                        sheetEditor.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, options));
                        int selected = options.indexOf(originalInputs.optString(key));
                        if (selected >= 0) sheetEditor.setSelection(selected);
                        editor = sheetEditor;
                    } else {
                        editor = numberInput(inputLabel(partCode, key), originalInputs.optString(key));
                    }
                    addLabeled(detail, inputLabel(partCode, key).toUpperCase(Locale.ROOT), editor);
                    editors.put(key, editor);
                }
                EditText itemQuantity = numberInput("Adet", String.valueOf(itemCount));
                addLabeled(detail, "ADET", itemQuantity);
                LinearLayout actions = new LinearLayout(this); actions.setPadding(0, dp(8), 0, 0);
                Button update = button("Guncelle", GREEN); Button remove = button("Sil", Color.rgb(151, 55, 47));
                LinearLayout.LayoutParams updateParams = new LinearLayout.LayoutParams(0, dp(48), 1); updateParams.rightMargin = dp(5); actions.addView(update, updateParams);
                LinearLayout.LayoutParams removeParams = new LinearLayout.LayoutParams(dp(82), dp(48)); removeParams.leftMargin = dp(5); actions.addView(remove, removeParams); detail.addView(actions);
                card.addView(detail);

                update.setOnClickListener(v -> {
                    try {
                        JSONObject updatedInputs = new JSONObject();
                        for (Map.Entry<String, View> entry : editors.entrySet()) {
                            View control = entry.getValue();
                            String value = control instanceof Spinner
                                ? String.valueOf(((Spinner) control).getSelectedItem())
                                : ((EditText) control).getText().toString().trim().replace(',', '.');
                            if (value.isEmpty()) throw new IllegalArgumentException("Tum olculeri girin.");
                            updatedInputs.put(entry.getKey(), value);
                        }
                        int updatedQuantity = Math.max(1, Integer.parseInt(itemQuantity.getText().toString()));
                        db.updateItem(profile, id, updatedInputs, updatedQuantity); toast("Sepet kalemi guncellendi.");
                        renderCartItems();
                    } catch (Exception error) { toast(error.getMessage()); }
                });
                remove.setOnClickListener(v -> { db.removeItem(profile, id); renderCartItems(); });
                headerRow.setOnClickListener(v -> {
                    boolean visible = detail.getVisibility() == View.VISIBLE;
                    detail.setVisibility(visible ? View.GONE : View.VISIBLE);
                    expandIcon.setText(visible ? "+" : "-");
                });
                itemList.addView(card);
            }
            if (values.length() == 0) itemList.addView(label("Henuz parca eklenmedi.", 14, MUTED, false));
        } catch (Exception error) { toast("Sepet acilamadi."); }
    }

    private String itemSummary(String partCode, JSONObject inputs, int quantity) {
        StringBuilder summary = new StringBuilder(); summary.append(quantity).append(" adet");
        String thickness = inputs.optString("sac_kalinlik_mm", "");
        if (!thickness.isEmpty()) summary.append(" · ").append(thickness).append(" mm");
        Iterator<String> keys = inputs.keys();
        int shown = 0;
        while (keys.hasNext() && shown < 2) {
            String key = keys.next();
            if ("sac_kalinlik_mm".equals(key)) continue;
            String value = inputs.optString(key);
            if (value.isEmpty()) continue;
            summary.append(" · ").append(inputLabel(partCode, key)).append(" ").append(value);
            shown++;
        }
        return summary.toString();
    }

    private String inputLabel(String partCode, String key) {
        if ("sac_kalinlik_mm".equals(key)) return "Sac kalinligi (mm)";
        try {
            for (int i = 0; i < parts.length(); i++) {
                JSONObject part = parts.getJSONObject(i);
                if (!partCode.equals(part.optString("code"))) continue;
                JSONArray definitions = part.optJSONArray("fields");
                for (int j = 0; definitions != null && j < definitions.length(); j++) {
                    JSONObject definition = definitions.getJSONObject(j);
                    if (key.equals(definition.optString("name"))) return definition.optString("label", key);
                }
            }
        } catch (Exception ignored) { }
        return key.replace('_', ' ');
    }

    private void saveHeader() {
        db.saveDraftHeader(profile, draftId, customer.getText().toString().trim(), customerPhone.getText().toString().trim(), 0, 0);
    }

    private void queueOperation(String type) {
        try {
            saveHeader();
            if ("submit_quote".equals(type) && db.items(profile, draftId).length() == 0) { toast("Teklif icin parca ekleyin."); return; }
            if ("submit_quote".equals(type) && customer.getText().toString().trim().isEmpty()) { toast("Musteri / firma adini girin."); return; }
            if ("submit_quote".equals(type) && customerPhone.getText().toString().replaceAll("\\D", "").length() < 10) { toast("Gecerli bir telefon numarasi girin."); return; }
            if ("submit_quote".equals(type)) {
                prefs.edit()
                    .putString("last_customer_" + profile, customer.getText().toString().trim())
                    .putString("last_phone_" + profile, customerPhone.getText().toString().trim())
                    .apply();
            }
            String operationId = UUID.randomUUID().toString(); JSONObject payload = db.operationPayload(profile, draftId, operationId, type);
            db.enqueue(profile, operationId, type, payload); SyncJobService.schedule(this); refreshQueueState();
            toast("submit_quote".equals(type) ? "Teklif senkron sirasina alindi." : "Taslak senkron sirasina alindi.");
            if ("submit_quote".equals(type)) {
                draftId = UUID.randomUUID().toString();
                prefs.edit().putString("draft_" + profile, draftId).apply();
                showDraft();
            }
        } catch (Exception error) { toast(error.getMessage()); }
    }

    private void restoreHeader() {
        try {
            JSONObject header = db.draftHeader(profile, draftId);
            customer.setText(header.optString("customer", prefs.getString("last_customer_" + profile, "")));
            customerPhone.setText(header.optString("customer_phone", prefs.getString("last_phone_" + profile, "")));
        } catch (Exception ignored) { }
    }

    private void refreshQueueState() {
        if (queueState == null) return;
        int waiting = db.count(profile, "pending"); int failed = db.count(profile, "failed");
        queueState.setText(waiting + " bekleyen islem" + (failed > 0 ? " / " + failed + " kalici hata" : ""));
        queueState.setTextColor(failed > 0 ? Color.rgb(151, 55, 47) : waiting > 0 ? ORANGE : GREEN);
    }

    private String profileKey(String server, String tenant) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest((server.toLowerCase(Locale.ROOT) + "|" + tenant).getBytes(StandardCharsets.UTF_8));
        StringBuilder value = new StringBuilder(); for (byte item : digest) value.append(String.format(Locale.ROOT, "%02x", item)); return value.toString();
    }

    private void toast(String message) { Toast.makeText(this, message == null ? "Islem basarisiz." : message, Toast.LENGTH_LONG).show(); }

    @Override public void onBackPressed() {
        if (cartOpen) showDraft(); else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        handler.removeCallbacksAndMessages(null); executor.shutdownNow(); db.close(); super.onDestroy();
    }
}
