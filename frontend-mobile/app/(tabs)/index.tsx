import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeButton } from '../../src/components/SafeButton';
import { useUnlockDevice } from '../../src/hooks/useUserMutations';
import { useEmergency } from '../../src/context/EmergencyContext';
import { ShieldCheck, PlusCircle } from 'lucide-react-native';

export default function HomeScreen() {
  const router = useRouter();
  const { triggerSOS } = useEmergency();

  // For MVP, hardcoding device ID that user might have paired
  const activeDevice = 'dev-001';

  const unlockMutation = useUnlockDevice();

  const handleUnlock = () => {
    // In real app, pass current GPS lat/lng
    unlockMutation.mutate({ deviceId: activeDevice });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.statusCard}>
        <View style={styles.statusHeader}>
          <Text style={styles.statusTitle}>Current Device</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>IDLE</Text>
          </View>
        </View>
        <Text style={styles.deviceName}>{activeDevice}</Text>
        <View style={styles.deviceInfo}>
          <ShieldCheck color="#10b981" size={20} />
          <Text style={styles.infoText}>Helmet paired</Text>
        </View>
        <SafeButton 
          title={unlockMutation.isPending ? "Unlocking..." : "Unlock to Ride"} 
          onPress={handleUnlock}
          disabled={unlockMutation.isPending}
          style={{ marginTop: 16 }}
        />
      </View>

      <TouchableOpacity style={styles.pairCard} onPress={() => router.push('/pair')}>
        <PlusCircle color="#3b82f6" size={24} />
        <Text style={styles.pairText}>Pair New Device</Text>
      </TouchableOpacity>

      <View style={{ flex: 1 }} />

      {/* SOS Button at the bottom — GlobalEmergencyOverlay handles the modal */}
      <View style={styles.sosContainer}>
        <Text style={styles.sosWarning}>Only use in emergencies</Text>
        <SafeButton
          title="EMERGENCY SOS"
          variant="danger"
          onPress={() => triggerSOS({ reason: 'User initiated SOS via Mobile App' })}
        />
      </View>
    </ScrollView>
  );
}


const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
    backgroundColor: '#f8fafc',
  },
  statusCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
    marginBottom: 20,
  },
  statusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusTitle: {
    fontSize: 14,
    color: '#64748b',
    textTransform: 'uppercase',
    fontWeight: '600',
  },
  badge: {
    backgroundColor: '#e2e8f0',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#475569',
  },
  deviceName: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 16,
  },
  deviceInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoText: {
    color: '#10b981',
    fontWeight: '500',
  },
  pairCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderStyle: 'dashed',
  },
  pairText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#3b82f6',
  },
  sosContainer: {
    marginTop: 40,
  },
  sosWarning: {
    textAlign: 'center',
    color: '#64748b',
    marginBottom: 8,
    fontSize: 14,
  }
});
