import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useUserProfile } from '../../src/hooks/useUserQueries';
import { User, Mail, Shield } from 'lucide-react-native';

export default function ProfileScreen() {
  const { data: profile, isLoading } = useUserProfile();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.avatar}>
          <User size={40} color="#3b82f6" />
        </View>
        <Text style={styles.name}>{profile?.name}</Text>
        <Text style={styles.email}>{profile?.email}</Text>
      </View>

      <View style={styles.scoreCard}>
        <View style={styles.scoreHeader}>
          <Shield color="#10b981" size={24} />
          <Text style={styles.scoreTitle}>Safety Score</Text>
        </View>
        <Text style={styles.scoreValue}>{profile?.safetyScore.toFixed(0)}</Text>
        <Text style={styles.scoreDesc}>Excellent! You are in the top 10% of safe riders.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 20,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
    marginTop: 20,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#eff6ff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  name: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 4,
  },
  email: {
    fontSize: 16,
    color: '#64748b',
  },
  scoreCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  scoreHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  scoreTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#0f172a',
  },
  scoreValue: {
    fontSize: 64,
    fontWeight: 'bold',
    color: '#10b981',
    marginBottom: 8,
  },
  scoreDesc: {
    textAlign: 'center',
    color: '#64748b',
    fontSize: 14,
  }
});
