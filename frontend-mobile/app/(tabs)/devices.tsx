import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Alert, TextInput, Modal, SafeAreaView,
} from 'react-native';
import { Bluetooth, Plus, Trash2, Wifi, WifiOff } from 'lucide-react-native';
import { useMyDevices } from '../../src/hooks/useUserQueries';
import { useRegisterDevice, useDeregisterDevice } from '../../src/hooks/useUserMutations';
import type { MyDevice } from '../../src/api/userApi';

const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: '#10b981',
  RUNNING_LIMITED: '#f59e0b',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: '#ef4444',
  IDLE: '#64748b',
  READY: '#3b82f6',
};

const STATE_LABELS: Record<string, string> = {
  RUNNING_NORMAL: '주행 중',
  RUNNING_LIMITED: '제한 주행',
  AUTO_BRAKING: '자동 제동',
  EMERGENCY: '긴급',
  IDLE: '대기',
  READY: '준비됨',
};

export default function DevicesScreen() {
  const { data: devices, isLoading, refetch } = useMyDevices();
  const registerMutation = useRegisterDevice();
  const deregisterMutation = useDeregisterDevice();

  const [modalVisible, setModalVisible] = useState(false);
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceType, setNewDeviceType] = useState('scooter');

  const handleRegister = () => {
    if (!newDeviceId.trim()) {
      Alert.alert('입력 오류', '디바이스 ID를 입력해 주세요.');
      return;
    }
    registerMutation.mutate(
      { deviceId: newDeviceId.trim(), deviceType: newDeviceType },
      {
        onSuccess: () => {
          setModalVisible(false);
          setNewDeviceId('');
        },
      },
    );
  };

  const handleDeregister = (device: MyDevice) => {
    Alert.alert(
      '디바이스 해제',
      `${device.deviceId}를 해제하시겠습니까?`,
      [
        { text: '취소', style: 'cancel' },
        { text: '해제', style: 'destructive', onPress: () => deregisterMutation.mutate(device.deviceId) },
      ],
    );
  };

  const renderDevice = ({ item }: { item: MyDevice }) => {
    const stateColor = STATE_COLORS[item.currentState] ?? '#64748b';
    return (
      <View style={styles.deviceCard}>
        <View style={styles.deviceLeft}>
          <View style={[styles.stateIndicator, { backgroundColor: stateColor }]} />
          <View>
            <Text style={styles.deviceId}>{item.deviceId}</Text>
            <Text style={styles.deviceType}>{STATE_LABELS[item.currentState] ?? item.currentState}</Text>
            <View style={styles.statusRow}>
              {item.bleConnected
                ? <Wifi size={12} color="#10b981" />
                : <WifiOff size={12} color="#64748b" />}
              <Text style={[styles.statusText, { color: item.bleConnected ? '#10b981' : '#64748b' }]}>
                {item.bleConnected ? '헬멧 연결됨' : '헬멧 미연결'}
              </Text>
            </View>
          </View>
        </View>
        <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDeregister(item)}>
          <Trash2 size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>내 디바이스</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModalVisible(true)}>
          <Plus size={20} color="#fff" />
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color="#3b82f6" />
      ) : (
        <FlatList
          data={devices ?? []}
          keyExtractor={(item) => item.deviceId}
          renderItem={renderDevice}
          contentContainerStyle={{ padding: 16, gap: 12 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Bluetooth size={48} color="#334155" />
              <Text style={styles.emptyText}>등록된 디바이스가 없습니다</Text>
              <Text style={styles.emptySubText}>+ 버튼으로 라즈베리파이를 등록하세요</Text>
            </View>
          }
          onRefresh={refetch}
          refreshing={isLoading}
        />
      )}

      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>디바이스 등록</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="디바이스 ID (예: pi-001)"
              placeholderTextColor="#64748b"
              value={newDeviceId}
              onChangeText={setNewDeviceId}
              autoCapitalize="none"
            />
            <View style={styles.typeRow}>
              {(['scooter', 'bike'] as const).map((t) => (
                <TouchableOpacity
                  key={t}
                  style={[styles.typeChip, newDeviceType === t && styles.typeChipActive]}
                  onPress={() => setNewDeviceType(t)}
                >
                  <Text style={[styles.typeChipText, newDeviceType === t && styles.typeChipTextActive]}>
                    {t === 'scooter' ? '킥보드' : '자전거'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity
              style={[styles.button, registerMutation.isPending && styles.buttonDisabled]}
              onPress={handleRegister}
              disabled={registerMutation.isPending}
            >
              {registerMutation.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.buttonText}>등록</Text>}
            </TouchableOpacity>
            <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
              <Text style={styles.cancelText}>취소</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingTop: 20, borderBottomWidth: 1, borderBottomColor: '#1e293b',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#f8fafc' },
  addBtn: {
    backgroundColor: '#3b82f6', width: 36, height: 36,
    borderRadius: 18, alignItems: 'center', justifyContent: 'center',
  },
  deviceCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1, borderColor: '#334155',
  },
  deviceLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  stateIndicator: { width: 10, height: 10, borderRadius: 5 },
  deviceId: { fontSize: 16, fontWeight: '700', color: '#f8fafc', marginBottom: 2 },
  deviceType: { fontSize: 12, color: '#64748b', marginBottom: 4 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statusText: { fontSize: 12, fontWeight: '500' },
  deleteBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 16, fontWeight: '600' },
  emptySubText: { color: '#64748b', fontSize: 13 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalBox: {
    backgroundColor: '#1e293b', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 28, gap: 16,
  },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#f8fafc' },
  modalInput: {
    backgroundColor: '#0f172a', borderRadius: 12, padding: 14,
    color: '#f8fafc', fontSize: 15, borderWidth: 1, borderColor: '#334155',
  },
  typeRow: { flexDirection: 'row', gap: 12 },
  typeChip: {
    flex: 1, padding: 12, borderRadius: 10, borderWidth: 1,
    borderColor: '#334155', alignItems: 'center',
  },
  typeChipActive: { borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)' },
  typeChipText: { color: '#94a3b8', fontWeight: '600' },
  typeChipTextActive: { color: '#3b82f6' },
  button: { backgroundColor: '#3b82f6', borderRadius: 12, padding: 16, alignItems: 'center' },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  cancelBtn: { alignItems: 'center', padding: 12 },
  cancelText: { color: '#64748b', fontSize: 15 },
});
