# Mobile App Plan — Companion Safety App

---

## Technology Choice: Flutter (iOS + Android from one codebase)

```bash
flutter create safety_companion
```

---

## App Screens

```
App Flow
├── Splash Screen → Login
├── Dashboard (Home)
│   ├── Device status (connected / offline)
│   ├── Battery level
│   ├── Threat level indicator
│   └── Quick SOS button
├── Alert History
│   ├── List of past alerts with timestamp
│   ├── Location map for each alert
│   └── Photo evidence (if available)
├── Emergency Contacts
│   ├── Add/edit contact numbers
│   └── Test SMS button
├── Settings
│   ├── Sensitivity sliders
│   ├── Alert preferences
│   └── Notification settings
└── Network Map (Mesh)
    └── Nearby devices in ad hoc network
```

---

## Core Flutter Code

### pubspec.yaml dependencies
```yaml
dependencies:
  flutter:
    sdk: flutter
  mqtt_client: ^9.7.4         # MQTT connection
  firebase_core: ^2.24.2      # Firebase
  firebase_messaging: ^14.7.6  # Push notifications
  google_maps_flutter: ^2.5.0  # Maps
  geolocator: ^10.1.0          # GPS location
  local_notifications: ^17.0.0 # Local alerts
  http: ^1.1.0                 # REST API calls
```

### MQTT Connection (lib/services/mqtt_service.dart)
```dart
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

class MQTTService {
  final client = MqttServerClient('broker.hivemq.com', 'safety_app_001');

  Future<void> connect() async {
    client.port = 1883;
    client.keepAlivePeriod = 60;
    await client.connect();
    client.subscribe('safety/alert', MqttQos.atLeastOnce);
    client.subscribe('safety/status', MqttQos.atMostOnce);

    client.updates!.listen((messages) {
      final msg = messages[0];
      final payload = MqttPublishPayload.bytesToStringAsString(
        (msg.payload as MqttPublishMessage).payload.message
      );
      _handleAlert(payload);
    });
  }

  void _handleAlert(String payload) {
    final data = jsonDecode(payload);
    final level = data['threat_level'];
    final details = data['details'];

    if (level >= 3) {
      // Trigger phone alarm + notification
      showEmergencyNotification(level, details);
    }
  }

  void publishSOS() {
    final builder = MqttClientPayloadBuilder();
    builder.addString('{"action": "sos", "source": "app"}');
    client.publishMessage('safety/command', MqttQos.atLeastOnce, builder.payload!);
  }
}
```

### Dashboard Screen (lib/screens/dashboard.dart)
```dart
import 'package:flutter/material.dart';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int threatLevel = 0;
  String status = "Safe";
  Color statusColor = Colors.green;

  void updateThreatLevel(int level) {
    setState(() {
      threatLevel = level;
      switch (level) {
        case 0: status = "Safe"; statusColor = Colors.green; break;
        case 1: status = "Aware"; statusColor = Colors.yellow; break;
        case 2: status = "Alert"; statusColor = Colors.orange; break;
        case 3: status = "Danger"; statusColor = Colors.red; break;
        case 4: status = "CRITICAL"; statusColor = Colors.red[900]!; break;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Safety Device"), backgroundColor: Colors.pink),
      body: Column(
        children: [
          // Status Circle
          Container(
            width: 200, height: 200,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: statusColor,
            ),
            child: Center(
              child: Text(status,
                style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)
              ),
            ),
          ),
          SizedBox(height: 40),
          // SOS Button
          ElevatedButton(
            onPressed: () => _triggerSOS(),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              minimumSize: Size(200, 60),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
            ),
            child: Text("SOS", style: TextStyle(fontSize: 28, color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _triggerSOS() {
    // Publish SOS via MQTT
    // Send SMS via backend API
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("SOS Sent"),
        content: Text("Emergency contacts have been notified."),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text("OK"))],
      ),
    );
  }
}
```

---

## Push Notifications (Firebase)

When threat level ≥ 3, the backend sends a push notification:
```
"DANGER ALERT — Your safety device detected a threat at [location].
 Tap to view details."
```

Setup:
1. Create Firebase project → firebase.google.com
2. Add Android/iOS app
3. Download `google-services.json` → android/app/
4. Enable Cloud Messaging in Firebase console
