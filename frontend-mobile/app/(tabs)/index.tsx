import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Play, Cpu, Shield, WifiOff, Wifi, LogOut } from 'lucide-react-native';
import { useMyDevices } from '../../src/hooks/useUserQueries';
import { useAuth } from '../../src/context/AuthContext';
import type { MyDevice } from '../../src/api/userApi';
import { SafeButton } from '../../src/components/SafeButton';
import { useEmergency } from '../../src/context/EmergencyContext';

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

export default function HomeScreen() {
  const router = useRouter();
  const { logout } = useAuth();
  const { triggerSOS } = useEmergency();
  const { data: devices, isLoading, refetch } = useMyDevices();

  const renderDevice = ({ item }: { item: MyDevice }) => {
    const stateColor = STATE_COLORS[item.currentState] ?? '#64748b';
    return (
      <View style={styles.deviceCard}>
        <View style={styles.deviceInfo}>
          <Cpu size={20} color={stateColor} />
          <View style={{ flex: 1 }}>
            <Text style={styles.deviceId}>{item.deviceId}</Text>
            <Text style={[styles.deviceState, { color: stateColor }]}>
              {STATE_LABELS[item.currentState] ?? item.currentState}
            </Text>
            <View style={styles.helmetRow}>
              <Shield size={12} color={item.helmetWorn ? '#10b981' : '#64748b'} />
              <Text style={[styles.helmetText, { color: item.helmetWorn ? '#10b981' : '#64748b' }]}>
                {item.helmetWorn ? '헬멧 착용' : '헬멧 미착용'}
              </Text>
              {item.bleConnected
                ? <Wifi size={12} color="#10b981" />
                : <WifiOff size={12} color="#64748b" />}
            </View>
          </View>
        </View>
        <TouchableOpacity
          style={styles.startBtn}
          onPress={() => router.push(`/riding/${item.deviceId}`)}
        >
          <Play size={16} color="#fff" />
          <Text style={styles.startBtnText}>주행 시작</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Safe Mobility</Text>
          <Text style={styles.subtitle}>안전한 주행을 시작하세요</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <LogOut size={20} color="#64748b" />
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color="#3b82f6" />
      ) : (
        <FlatList
          data={devices ?? []}
          keyExtractor={(item) => item.deviceId}
          renderItem={renderDevice}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 120 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Cpu size={48} color="#334155" />
              <Text style={styles.emptyText}>등록된 디바이스가 없습니다</Text>
              <Text style={styles.emptySubText}>디바이스 탭에서 라즈베리파이를 등록하세요</Text>
            </View>
          }
          onRefresh={refetch}
          refreshing={isLoading}
        />
      )}

      <View style={styles.sosContainer}>
        <Text style={styles.sosWarning}>긴급 상황에서만 사용하세요</Text>
        <SafeButton
          title="긴급 SOS"
          variant="danger"
          onPress={() => triggerSOS({ reason: '사용자 SOS (모바일 앱)' })}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingTop: 24,
  },
  greeting: { fontSize: 22, fontWeight: '800', color: '#f8fafc' },
  subtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  logoutBtn: { padding: 8 },
  deviceCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    borderWidth: 1, borderColor: '#334155', gap: 12,
  },
  deviceInfo: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  deviceId: { fontSize: 16, fontWeight: '700', color: '#f8fafc', marginBottom: 2 },
  deviceState: { fontSize: 13, fontWeight: '600', marginBottom: 4 },
  helmetRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  helmetText: { fontSize: 12, fontWeight: '500' },
  startBtn: {
    backgroundColor: '#3b82f6', borderRadius: 10, padding: 12,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
  },
  startBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 16, fontWeight: '600' },
  emptySubText: { color: '#64748b', fontSize: 13, textAlign: 'center' },
  sosContainer: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    padding: 20, backgroundColor: '#0f172a',
    borderTopWidth: 1, borderTopColor: '#1e293b',
  },
  sosWarning: { textAlign: 'center', color: '#64748b', fontSize: 12, marginBottom: 8 },
});
