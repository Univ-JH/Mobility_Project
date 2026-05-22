import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { Shield, MapPin, Activity, AlertOctagon, Unlock, Lock } from 'lucide-react-native';
import { userApi } from '../../src/api/userApi';

export default function DashboardScreen() {
  // Prototype State
  const [helmetWorn, setHelmetWorn] = useState(true);
  const [deviceLocked, setDeviceLocked] = useState(false);
  const [drivingMode, setDrivingMode] = useState('ROAD'); // 'ROAD' | 'SIDEWALK'
  const [emergency, setEmergency] = useState(false);

  // Simulate incoming MQTT events
  useEffect(() => {
    const timer = setInterval(() => {
      // randomly switch to sidewalk for prototype demonstration
      if (Math.random() > 0.8) {
        setDrivingMode(prev => prev === 'ROAD' ? 'SIDEWALK' : 'ROAD');
      }
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const triggerEmergency = () => {
    setEmergency(true);
    Alert.alert(
      "⚠️ EMERGENCY DETECTED",
      "Crash or sudden fall detected. Sending SOS to guardian in 10 seconds. Cancel if false alarm.",
      [
        { text: "Cancel SOS", onPress: () => setEmergency(false), style: "cancel" },
        { 
          text: "Send Now", 
          onPress: async () => {
            setEmergency(false);
            try {
              userApi.triggerEmergency("User requested SOS from Mobile Prototype", 37.5665, 126.9780);
              Alert.alert("SOS Sent", "Emergency contacts and admins have been notified.");
            } catch (e) {
              Alert.alert("Error", "Failed to send SOS.");
            }
          }, 
          style: "destructive" 
        }
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Safe Ride,</Text>
            <Text style={styles.userName}>Alex</Text>
          </View>
          <View style={styles.deviceStatusBadge}>
            <View style={[styles.statusDot, { backgroundColor: '#10b981' }]} />
            <Text style={styles.statusText}>PI-Alpha</Text>
          </View>
        </View>

        {/* Emergency Alert Tester (Prototype Only) */}
        <TouchableOpacity style={styles.testEmergencyBtn} onPress={triggerEmergency}>
          <AlertOctagon size={20} color="#fff" />
          <Text style={styles.testEmergencyText}>Simulate Crash</Text>
        </TouchableOpacity>

        {/* Status Cards */}
        <View style={styles.cardRow}>
          {/* Helmet Status */}
          <TouchableOpacity 
            style={[styles.card, styles.halfCard, helmetWorn ? styles.cardSuccess : styles.cardDanger]}
            onPress={() => setHelmetWorn(!helmetWorn)}
          >
            <Shield size={32} color={helmetWorn ? '#10b981' : '#ef4444'} />
            <Text style={styles.cardTitle}>Helmet</Text>
            <Text style={[styles.cardValue, { color: helmetWorn ? '#10b981' : '#ef4444' }]}>
              {helmetWorn ? 'WORN' : 'UNWORN'}
            </Text>
          </TouchableOpacity>

          {/* Lock Status */}
          <TouchableOpacity 
            style={[styles.card, styles.halfCard]}
            onPress={() => setDeviceLocked(!deviceLocked)}
          >
            {deviceLocked ? <Lock size={32} color="#f59e0b" /> : <Unlock size={32} color="#3b82f6" />}
            <Text style={styles.cardTitle}>Device</Text>
            <Text style={[styles.cardValue, { color: deviceLocked ? '#f59e0b' : '#3b82f6' }]}>
              {deviceLocked ? 'LOCKED' : 'ACTIVE'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Driving Mode Display */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MapPin size={24} color="#94a3b8" />
            <Text style={styles.cardTitle}>Current Environment</Text>
          </View>
          <View style={styles.modeContainer}>
            <Text style={[styles.modeText, drivingMode === 'ROAD' ? styles.modeSafe : styles.modeWarning]}>
              {drivingMode === 'ROAD' ? 'Safe Road' : 'Sidewalk Detected!'}
            </Text>
            {drivingMode === 'SIDEWALK' && (
              <Text style={styles.modeSubText}>Speed limited to 5km/h for safety.</Text>
            )}
          </View>
        </View>

        {/* Recent Alerts */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Alerts</Text>
        </View>
        
        <View style={styles.alertList}>
          <View style={styles.alertItem}>
            <View style={styles.alertIconBgWarning}>
              <Activity size={20} color="#f59e0b" />
            </View>
            <View style={styles.alertContent}>
              <Text style={styles.alertItemTitle}>Sudden Brake</Text>
              <Text style={styles.alertItemTime}>Today, 10:45 AM</Text>
            </View>
          </View>
          
          <View style={styles.alertItem}>
            <View style={styles.alertIconBgDanger}>
              <Shield size={20} color="#ef4444" />
            </View>
            <View style={styles.alertContent}>
              <Text style={styles.alertItemTitle}>Helmet Removed While Riding</Text>
              <Text style={styles.alertItemTime}>Yesterday, 04:20 PM</Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  scrollContent: { padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  greeting: { fontSize: 16, color: '#94a3b8' },
  userName: { fontSize: 24, fontWeight: '700', color: '#f8fafc' },
  deviceStatusBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1e293b', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: '#334155' },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  statusText: { color: '#e2e8f0', fontSize: 14, fontWeight: '500' },
  testEmergencyBtn: { flexDirection: 'row', backgroundColor: '#ef4444', padding: 12, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginBottom: 24, gap: 8 },
  testEmergencyText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  cardRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16, gap: 16 },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 20, borderWidth: 1, borderColor: '#334155', marginBottom: 16 },
  halfCard: { flex: 1, alignItems: 'center', paddingVertical: 24 },
  cardSuccess: { borderColor: 'rgba(16, 185, 129, 0.3)', backgroundColor: 'rgba(16, 185, 129, 0.05)' },
  cardDanger: { borderColor: 'rgba(239, 68, 68, 0.3)', backgroundColor: 'rgba(239, 68, 68, 0.05)' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 8 },
  cardTitle: { fontSize: 14, color: '#94a3b8', marginTop: 12 },
  cardValue: { fontSize: 20, fontWeight: '700', marginTop: 4 },
  modeContainer: { alignItems: 'center', paddingVertical: 10 },
  modeText: { fontSize: 28, fontWeight: '800' },
  modeSafe: { color: '#10b981' },
  modeWarning: { color: '#f59e0b' },
  modeSubText: { color: '#ef4444', marginTop: 8, fontWeight: '500' },
  sectionHeader: { marginTop: 8, marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#f8fafc' },
  alertList: { gap: 12 },
  alertItem: { flexDirection: 'row', backgroundColor: '#1e293b', padding: 16, borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  alertIconBgWarning: { backgroundColor: 'rgba(245, 158, 11, 0.1)', padding: 10, borderRadius: 10, marginRight: 16 },
  alertIconBgDanger: { backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: 10, borderRadius: 10, marginRight: 16 },
  alertContent: { flex: 1 },
  alertItemTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '500', marginBottom: 4 },
  alertItemTime: { color: '#94a3b8', fontSize: 12 },
});
