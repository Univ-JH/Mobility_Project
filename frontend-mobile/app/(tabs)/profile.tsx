import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, ScrollView } from 'react-native';
import { User, ShieldCheck, History, Settings, ChevronRight } from 'lucide-react-native';

export default function ProfileScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={styles.avatar}>
            <User size={40} color="#3b82f6" />
          </View>
          <Text style={styles.name}>Alex User</Text>
          <Text style={styles.email}>alex@safemobility.test</Text>
        </View>

        <View style={styles.scoreCard}>
          <Text style={styles.scoreTitle}>Safety Score</Text>
          <View style={styles.scoreCircle}>
            <Text style={styles.scoreValue}>92</Text>
          </View>
          <Text style={styles.scoreDesc}>Excellent Rider! Keep it up.</Text>
        </View>

        <View style={styles.menuList}>
          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIconBg}><ShieldCheck size={20} color="#10b981" /></View>
            <Text style={styles.menuText}>Emergency Contacts</Text>
            <ChevronRight size={20} color="#64748b" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIconBg}><History size={20} color="#f59e0b" /></View>
            <Text style={styles.menuText}>Ride History</Text>
            <ChevronRight size={20} color="#64748b" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIconBg}><Settings size={20} color="#94a3b8" /></View>
            <Text style={styles.menuText}>App Settings</Text>
            <ChevronRight size={20} color="#64748b" />
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  scrollContent: { padding: 20 },
  header: { alignItems: 'center', marginTop: 20, marginBottom: 32 },
  avatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(59, 130, 246, 0.1)', alignItems: 'center', justifyContent: 'center', marginBottom: 16, borderWidth: 1, borderColor: 'rgba(59, 130, 246, 0.3)' },
  name: { fontSize: 24, fontWeight: '700', color: '#f8fafc', marginBottom: 4 },
  email: { fontSize: 14, color: '#94a3b8' },
  scoreCard: { backgroundColor: '#1e293b', borderRadius: 16, padding: 24, alignItems: 'center', borderWidth: 1, borderColor: '#334155', marginBottom: 32 },
  scoreTitle: { fontSize: 16, color: '#94a3b8', marginBottom: 16 },
  scoreCircle: { width: 100, height: 100, borderRadius: 50, borderWidth: 4, borderColor: '#10b981', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  scoreValue: { fontSize: 36, fontWeight: '800', color: '#10b981' },
  scoreDesc: { fontSize: 14, color: '#f8fafc', fontWeight: '500' },
  menuList: { gap: 12 },
  menuItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1e293b', padding: 16, borderRadius: 12, borderWidth: 1, borderColor: '#334155' },
  menuIconBg: { backgroundColor: '#0f172a', padding: 8, borderRadius: 8, marginRight: 16 },
  menuText: { flex: 1, fontSize: 16, color: '#f8fafc', fontWeight: '500' },
});
