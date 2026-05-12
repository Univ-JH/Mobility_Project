import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeButton } from '../src/components/SafeButton';
import { usePairDevice } from '../src/hooks/useUserMutations';
import { Bluetooth } from 'lucide-react-native';

export default function PairScreen() {
  const router = useRouter();
  const [scanning, setScanning] = useState(true);
  const pairMutation = usePairDevice();

  useEffect(() => {
    // Simulate BLE Scanning delay
    const timer = setTimeout(() => {
      setScanning(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handlePair = () => {
    pairMutation.mutate(
      { deviceId: 'dev-001', type: 'scooter' },
      {
        onSuccess: () => {
          router.back();
        }
      }
    );
  };

  return (
    <View style={styles.container}>
      {scanning ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3b82f6" />
          <Text style={styles.text}>Scanning for nearby devices...</Text>
        </View>
      ) : (
        <View style={styles.content}>
          <View style={styles.iconContainer}>
            <Bluetooth size={40} color="#3b82f6" />
          </View>
          <Text style={styles.title}>Device Found!</Text>
          
          <View style={styles.deviceCard}>
            <Text style={styles.deviceName}>dev-001</Text>
            <Text style={styles.deviceType}>Mobility Scooter</Text>
          </View>

          <SafeButton 
            title={pairMutation.isPending ? "Pairing..." : "Connect Device"}
            onPress={handlePair}
            disabled={pairMutation.isPending}
            style={{ marginTop: 40 }}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  text: {
    color: '#64748b',
    fontSize: 16,
  },
  content: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    width: 80, height: 80,
    borderRadius: 40,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 32,
  },
  deviceCard: {
    width: '100%',
    backgroundColor: 'white',
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  deviceName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 8,
  },
  deviceType: {
    fontSize: 16,
    color: '#64748b',
  }
});
