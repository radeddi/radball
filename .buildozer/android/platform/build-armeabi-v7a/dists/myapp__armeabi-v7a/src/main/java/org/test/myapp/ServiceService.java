package org.test.myapp;

import android.content.Intent;
import android.content.Context;
import org.kivy.android.PythonService;


public class ServiceService extends PythonService {
    

    @Override
    protected int getServiceId() {
        return 1;
    }

    static public void start(Context ctx, String pythonServiceArgument) {
        Intent intent = new Intent(ctx, ServiceService.class);
        String argument = ctx.getFilesDir().getAbsolutePath() + "/app";
        intent.putExtra("androidPrivate", ctx.getFilesDir().getAbsolutePath());
        intent.putExtra("androidArgument", argument);
        intent.putExtra("serviceTitle", "My Application");
        intent.putExtra("serviceDescription", "Service");
        intent.putExtra("serviceEntrypoint", "service.py");
        intent.putExtra("pythonName", "service");
        intent.putExtra("serviceStartAsForeground", "false");
        intent.putExtra("pythonHome", argument);
        intent.putExtra("pythonPath", argument + ":" + argument + "/lib");
        intent.putExtra("pythonServiceArgument", pythonServiceArgument);
        ctx.startService(intent);
    }

    static public void stop(Context ctx) {
        Intent intent = new Intent(ctx, ServiceService.class);
        ctx.stopService(intent);
    }
}