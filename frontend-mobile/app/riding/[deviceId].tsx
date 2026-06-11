import React from 'react';
import {
  View, Text, StyleSheet, SafeAreaView, ScrollView,
  TouchableOpacity, FlatList,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Shield, MapPin, Wifi, WifiOff, ChevronLeft, AlertTriangle } from 'lucide-react-native';
import { useRidingWebSocket } from '../../src/hooks/useRidingWebSocket';
import type { RidingEvent } from '../../src/hooks/useRidingWebSocket';

const ROAD_TYPE_LABEL: Record<string, string> = {
  road: '도로',
  sidewalk: '인도',
  unknown: '감지 중...',
};

const ROAD_TYPE_COLOR: Record<string, string> = {
  road: '#10b981',
  sidewalk: '#f59e0b',
  unknown: '#64748b',
};

const SEVERITY_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#3b82f6',
};

export default function RidingScreen() {
  const { deviceId } = useLocalSearchParams<{ deviceId: string }>();
  const router = useRouter();
  const { data, events, connected } = useRidingWebSocket(deviceId ?? '');

  const roadColor = ROAD_TYPE_COLOR[data.roadType] ?? '#64748b';

  const renderEvent = ({ item }: { item: RidingEvent }) => (
    <View style={[styles.eventItem, { borderLeftColor: SEVERITY_COLOR[item.severity] ?? '#64748b' }]}>
      <View style={styles.eventHeader}>
        <Text style={styles.eventType}>{item.eventType}</Text>
        <Text style={[styles.eventSeverity, { color: SEVERITY_COLOR[item.severity] ?? '#64748b' }]}>
          {item.severity.toUpperCase()}
        </Text>
      </View>
      <Text style={styles.eventReason}>{item.reason}</Text>
      <Text style={styles.eventTime}>
        {new Date(item.timestamp).toLocaleTimeString('ko-KR')}
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <ChevronLeft size={28} color="#f8fafc" />
        </TouchableOpacity>
        <Text style={styles.deviceTitle} numberOfLines={1}>{deviceId}</Text>
        <View style={styles.connBadge}>
          {connected
            ? <Wifi size={14} color="#10b981" />
            : <WifiOff size={14} color="#ef4444" />}
          <Text style={[styles.connText, { color: connected ? '#10b981' : '#ef4444' }]}>
            {connected ? 'Live' : '연결 끊김'}
          </Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.speedCard}>
          <Text style={styles.speedLabel}>현재 속력</Text>
          <Text style={styles.speedValue}>{data.speedKph.toFixed(1)}</Text>
          <Text style={styles.speedUnit}>km/h</Text>
          {data.roadType === 'sidewalk' && (
            <View style={styles.warningBanner}>
              <AlertTriangle size={14} color="#f59e0b" />
              <Text style={styles.warningText}>인도 감지 — 속도 제한 적용 중</Text>
            </View>
          )}
        </View>

        <View style={[styles.statusCard, { borderLeftColor: roadColor }]}>
          <MapPin size={22} color={roadColor} />
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>도로 유형</Text>
            <Text style={[styles.statusValue, { color: roadColor }]}>
              {ROAD_TYPE_LABEL[data.roadType] ?? '알 수 없음'}
            </Text>
          </View>
        </View>

        <View style={[styles.statusCard, {
          borderLeftColor: data.helmetWorn ? '#10b981' : '#ef4444',
        }]}>
          <Shield size={22} color={data.helmetWorn ? '#10b981' : '#ef4444'} />
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>헬멧 상태</Text>
            <Text style={[styles.statusValue, { color: data.helmetWorn ? '#10b981' : '#ef4444' }]}>
              {data.helmetWorn ? '착용 중' : '미착용 ⚠️'}
            </Text>
          </View>
        </View>

        <View style={[styles.statusCard, {
          borderLeftColor: data.bleConnected ? '#10b981' : '#64748b',
        }]}>
          {data.bleConnected
            ? <Wifi size={22} color="#10b981" />
            : <WifiOff size={22} color="#64748b" />}
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>헬멧 BLE 연결</Text>
            <Text style={[styles.statusValue, { color: data.bleConnected ? '#10b981' : '#64748b' }]}>
              {data.bleConnected ? '연결됨' : '연결 안 됨'}
            </Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>주행 이벤트</Text>
        {events.length === 0 ? (
          <View style={styles.noEvents}>
            <Text style={styles.noEventsText}>이벤트 없음</Text>
          </View>
        ) : (
          <FlatList
            data={events}
            keyExtractor={(item) => `${item.eventType}-${item.timestamp}`}
            renderItem={renderEvent}
            scrollEnabled={false}
            contentContainerStyle={{ gap: 8 }}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  topBar: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16,
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1e293b',
  },
  backBtn: { marginRight: 8 },
  deviceTitle: { flex: 1, fontSize: 18, fontWeight: '700', color: '#f8fafc' },
  connBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, marginLeft: 8 },
  connText: { fontSize: 12, fontWeight: '600' },
  scroll: { padding: 16, gap: 12, paddingBottom: 40 },
  speedCard: {
    backgroundColor: '#1e293b', borderRadius: 20, padding: 28,
    alignItems: 'center', borderWidth: 1, borderColor: '#334155',
  },
  speedLabel: { fontSize: 14, color: '#94a3b8', marginBottom: 4 },
  speedValue: { fontSize: 72, fontWeight: '800', color: '#f8fafc', lineHeight: 80 },
  speedUnit: { fontSize: 18, color: '#64748b', marginTop: 4 },
  warningBanner: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: 'rgba(245,158,11,0.1)', borderRadius: 8,
    paddingHorizontal: 12, paddingVertical: 6, marginTop: 12,
  },
  warningText: { fontSize: 13, color: '#f59e0b', fontWeight: '500' },
  statusCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    flexDirection: 'row', alignItems: 'center', gap: 14,
    borderLeftWidth: 4, borderColor: '#334155', borderWidth: 1,
  },
  statusCardContent: { flex: 1 },
  statusLabel: { fontSize: 12, color: '#64748b', marginBottom: 2 },
  statusValue: { fontSize: 18, fontWeight: '700' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#94a3b8', marginTop: 8 },
  noEvents: { backgroundColor: '#1e293b', borderRadius: 12, padding: 24, alignItems: 'center' },
  noEventsText: { color: '#64748b', fontSize: 14 },
  eventItem: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 14,
    borderLeftWidth: 3, borderColor: '#334155', borderWidth: 1,
  },
  eventHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  eventType: { fontSize: 14, fontWeight: '700', color: '#f8fafc' },
  eventSeverity: { fontSize: 11, fontWeight: '700' },
  eventReason: { fontSize: 13, color: '#94a3b8', marginBottom: 4 },
  eventTime: { fontSize: 11, color: '#64748b' },
});
