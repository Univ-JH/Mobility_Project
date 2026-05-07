import { router } from 'expo-router';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ActivityIndicator } from 'react-native';
import { Bluetooth, CheckCircle2 } from 'lucide-react-native';
import { useState } from 'react';

export default function PairingScreen() {
  const [isScanning, setIsScanning] = useState(false);
  const [deviceFound, setDeviceFound] = useState(false);

  const startScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setDeviceFound(true);
    }, 2000);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backText}>Cancel</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.content}>
        <View style={styles.circleContainer}>
          {isScanning ? (
            <ActivityIndicator size="large" color="#3b82f6" />
          ) : deviceFound ? (
            <CheckCircle2 size={64} color="#10b981" />
          ) : (
            <Bluetooth size={64} color="#3b82f6" />
          )}
        </View>

        <Text style={styles.title}>
          {isScanning ? 'Scanning for Helmet...' : deviceFound ? 'Helmet Paired!' : 'Pair Your Helmet'}
        </Text>
        <Text style={styles.subtitle}>
          {isScanning 
            ? 'Please keep your helmet close to your phone.' 
            : deviceFound 
            ? 'Your device PI-Alpha is successfully connected.'
            : 'Turn on your smart helmet and make sure Bluetooth is enabled.'}
        </Text>

        {deviceFound && (
          <View style={styles.deviceCard}>
            <View style={styles.deviceInfo}>
              <Text style={styles.deviceName}>PI-Alpha Smart Helmet</Text>
              <Text style={styles.deviceStatus}>Connected • Battery 85%</Text>
            </View>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        <TouchableOpacity 
          style={[styles.button, deviceFound ? styles.successButton : styles.primaryButton]}
          onPress={deviceFound ? () => router.push('/(tabs)/dashboard') : startScan}
          disabled={isScanning}
        >
          <Text style={styles.buttonText}>
            {isScanning ? 'Scanning...' : deviceFound ? 'Go to Dashboard' : 'Start Pairing'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: { padding: 20, alignItems: 'flex-start' },
  backButton: { paddingVertical: 8 },
  backText: { color: '#94a3b8', fontSize: 16 },
  content: { flex: 1, alignItems: 'center', padding: 24, paddingTop: 40 },
  circleContainer: {
    width: 140, height: 140, borderRadius: 70,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    alignItems: 'center', justifyContent: 'center',
    marginBottom: 32,
    borderWidth: 1, borderColor: 'rgba(59, 130, 246, 0.3)',
  },
  title: { fontSize: 24, fontWeight: '700', color: '#f8fafc', marginBottom: 12 },
  subtitle: { fontSize: 16, color: '#94a3b8', textAlign: 'center', lineHeight: 24, paddingHorizontal: 20 },
  deviceCard: {
    marginTop: 40, width: '100%', padding: 16,
    backgroundColor: '#1e293b', borderRadius: 12,
    borderWidth: 1, borderColor: '#334155',
  },
  deviceInfo: { justifyContent: 'center' },
  deviceName: { fontSize: 16, fontWeight: '600', color: '#f8fafc', marginBottom: 4 },
  deviceStatus: { fontSize: 14, color: '#10b981' },
  footer: { padding: 24 },
  button: { padding: 16, borderRadius: 12, alignItems: 'center' },
  primaryButton: { backgroundColor: '#3b82f6' },
  successButton: { backgroundColor: '#10b981' },
  buttonText: { color: '#ffffff', fontSize: 16, fontWeight: '700' },
});
