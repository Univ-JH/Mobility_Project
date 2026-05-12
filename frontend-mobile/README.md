# Frontend Mobile (React Native / Expo)

This folder contains the React Native (Expo) Mobile Application for the Safe Mobility System.

## Prototype Implementation
Currently, the application is built as a **prototype**, providing a modern, dark-themed UI that simulates device pairing, real-time safety monitoring, and emergency handling. It uses `expo-router` for file-based navigation.

### Key Files and Descriptions:
*   `app/index.tsx`: **Onboarding Screen.** Introduces the core value of the Safe Mobility System. Provides navigation to the Pairing screen or bypasses to the Dashboard.
*   `app/pairing.tsx`: **Device Pairing Screen.** Simulates scanning and connecting via Bluetooth to the Raspberry Pi device (e.g., PI-Alpha).
*   `app/(tabs)/_layout.tsx`: **Tab Navigation.** Configures the bottom tab bar with customized styling and `lucide-react-native` icons, linking to the Dashboard and Profile tabs.
*   `app/(tabs)/dashboard.tsx`: **Main Dashboard Screen.**
    *   **Features:** Displays real-time device stats (Helmet WORN/UNWORN, Device Locked/Active). Includes a live 'Current Environment' card that randomly switches between "Safe Road" and "Sidewalk Detected" to simulate AI vision inputs.
    *   **Emergency Simulation:** Contains a "Simulate Crash" button that triggers a high-priority system alert (React Native `Alert.alert`), implementing the fail-safe notification UX flow.
*   `app/(tabs)/profile.tsx`: **User Profile Screen.** Displays the user's safety score, recent ride history, and settings (Mock UI).

## Future AWS & MQTT Integration
When transitioning from the prototype to production:
1.  **Real-Time Data (MQTT):** Replace the simulated `setInterval` logic in `dashboard.tsx` with an actual MQTT client subscription to your AWS IoT / Backend broker to receive real-time device telemetry.
2.  **API Fetch (FastAPI/MongoDB):** Replace the hardcoded alerts and user profile data with data fetched from your backend REST API.
3.  **Bluetooth (BLE):** Replace the mocked `setTimeout` pairing flow in `pairing.tsx` with a native BLE library (e.g., `react-native-ble-plx`) to communicate directly with the Arduino helmet.

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the Expo development server:
   ```bash
   npx expo start
   ```
