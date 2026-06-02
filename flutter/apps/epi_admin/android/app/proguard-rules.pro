# Flutter wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-keep class io.flutter.embedding.** { *; }
-dontwarn io.flutter.embedding.**

# Dart/Flutter reflection
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes InnerClasses

# Firebase Messaging
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# ML Kit (text recognition)
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**

# OkHttp / Dio (network layer)
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }

# Gson / JSON serialization
-keepclassmembers class ** {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Kotlin coroutines
-dontwarn kotlinx.coroutines.**

# Keep app entry point
-keep class com.rocksbrothers.epicontrole.** { *; }
