import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  FlatList, TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Bluetooth, Radio } from 'lucide-react-native';
import { SafeButton } from '../src/components/SafeButton';
import { usePairDevice } from '../src/hooks/useUserMutations';
import { userApi, type AvailableDevice } from '../src/api/userApi';

const DEVICE_TYPES = [
  { value: 'scooter', label: '킥보드' },
  { value: 'bike', label: '자전거' },
  { value: 'ebike', label: '전동 자전거' },
] as const;

type DeviceTypeValue = typeof DEVICE_TYPES[number]['value'];

export default function PairScreen() {
  const router = useRouter();
  const [selectedDevice, setSelectedDevice] = useState<AvailableDevice | null>(null);
  const [selectedType, setSelectedType] = useState<DeviceTypeValue>('scooter');
  const pairMutation = usePairDevice();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['availableDevices'],
    queryFn: async () => {
      const res = await userApi.getAvailableDevices();
      return res.data.devices;
    },
    refetchInterval: 5000,
    retry: false,
  });

  const devices = data ?? [];

  const handlePair = () => {
    if (!selectedDevice) return;
    pairMutation.mutate(
      { deviceId: selectedDevice.deviceId, type: selectedType },
      { onSuccess: () => router.back() },
    );
  };

  if (isLoading && devices.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.scanText}>주변 디바이스 검색 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          발견된 디바이스 {isLoading && <ActivityIndicator size="small" color="#3b82f6" />}
        </Text>

        {devices.length === 0 ? (
          <View style={styles.empty}>
            <Bluetooth size={40} color="#334155" />
            <Text style={styles.emptyText}>주변에 디바이스가 없습니다</Text>
            <TouchableOpacity onPress={() => refetch()}>
              <Text style={styles.retryText}>다시 검색</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={devices}
            keyExtractor={(item) => item.deviceId}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  styles.deviceCard,
                  selectedDevice?.deviceId === item.deviceId && styles.deviceCardSelected,
                ]}
                onPress={() => setSelectedDevice(item)}
              >
                <Radio size={20} color={selectedDevice?.deviceId === item.deviceId ? '#3b82f6' : '#64748b'} />
                <Text style={[
                  styles.deviceId,
                  selectedDevice?.deviceId === item.deviceId && styles.deviceIdSelected,
                ]}>
                  {item.deviceId}
                </Text>
              </TouchableOpacity>
            )}
          />
        )}
      </View>

      {selectedDevice && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>디바이스 타입</Text>
          <View style={styles.typeRow}>
            {DEVICE_TYPES.map((t) => (
              <TouchableOpacity
                key={t.value}
                style={[styles.typeChip, selectedType === t.value && styles.typeChipActive]}
                onPress={() => setSelectedType(t.value)}
              >
                <Text style={[styles.typeChipText, selectedType === t.value && styles.typeChipTextActive]}>
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      <SafeButton
        title={pairMutation.isPending ? '연결 중...' : '연결하기'}
        onPress={handlePair}
        disabled={!selectedDevice || pairMutation.isPending}
        style={styles.button}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', padding: 20 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  scanText: { color: '#64748b', fontSize: 16 },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#64748b', letterSpacing: 1, marginBottom: 12 },
  empty: { alignItems: 'center', paddingVertical: 32, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 15 },
  retryText: { color: '#3b82f6', fontSize: 14, fontWeight: '600' },
  deviceCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: 16, borderRadius: 12, backgroundColor: '#fff',
    borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 8,
  },
  deviceCardSelected: { borderColor: '#3b82f6', backgroundColor: '#eff6ff' },
  deviceId: { fontSize: 16, fontWeight: '600', color: '#334155' },
  deviceIdSelected: { color: '#3b82f6' },
  typeRow: { flexDirection: 'row', gap: 10 },
  typeChip: {
    flex: 1, padding: 12, borderRadius: 10,
    borderWidth: 1, borderColor: '#e2e8f0', alignItems: 'center',
    backgroundColor: '#fff',
  },
  typeChipActive: { borderColor: '#3b82f6', backgroundColor: '#eff6ff' },
  typeChipText: { color: '#94a3b8', fontWeight: '600', fontSize: 14 },
  typeChipTextActive: { color: '#3b82f6' },
  button: { marginTop: 'auto' },
});
