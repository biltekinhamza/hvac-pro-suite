package com.hvac.pro.mobile;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SyncJobService extends JobService {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    static void schedule(Context context) {
        JobInfo job = new JobInfo.Builder(7319, new ComponentName(context, SyncJobService.class))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setMinimumLatency(1000).setBackoffCriteria(30000, JobInfo.BACKOFF_POLICY_EXPONENTIAL).build();
        context.getSystemService(JobScheduler.class).schedule(job);
    }

    @Override public boolean onStartJob(JobParameters params) {
        executor.execute(() -> {
            SharedPreferences prefs = getSharedPreferences("connection", MODE_PRIVATE);
            String server = prefs.getString("server", "");
            String token = prefs.getString("token", "");
            String profile = prefs.getString("profile", "");
            QueueDb db = new QueueDb(this);
            if (!server.isEmpty() && !token.isEmpty() && !profile.isEmpty()) {
                for (QueueDb.Pending pending : db.pending(profile)) {
                    try {
                        ApiClient.Result result = ApiClient.post(server, "/api/v1/operations", token, new JSONObject(pending.payload));
                        if (result.ok()) db.complete(pending.id);
                        else if (result.status == 401 || result.status == 403) break;
                        else if (result.status >= 400 && result.status < 500) db.fail(pending.id, result.message());
                        else handleRetry(db, pending, result.message());
                    } catch (Exception error) {
                        handleRetry(db, pending, error.getMessage());
                        break;
                    }
                }
            }
            jobFinished(params, db.count(profile, "pending") > 0);
        });
        return true;
    }

    private void handleRetry(QueueDb db, QueueDb.Pending pending, String error) {
        int attempts = pending.attempts + 1;
        if (attempts >= 8) db.fail(pending.id, error == null ? "Baglanti hatasi" : error);
        else db.retry(pending.id, attempts, error == null ? "Baglanti hatasi" : error);
    }

    @Override public boolean onStopJob(JobParameters params) { return true; }
}
