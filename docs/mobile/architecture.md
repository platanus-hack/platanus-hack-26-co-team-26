# Mobile architecture

Compose UI consumes route-level state and delegates hardware to ports. `:core` owns pure domain and signal processing. Android implementations live in `:android:sensing` and `:android:ppg`. The current shell uses a small route enum to keep navigation centralized while the feature set is still a foundation; it can migrate to Navigation Compose when routes become independently deep-linkable.

