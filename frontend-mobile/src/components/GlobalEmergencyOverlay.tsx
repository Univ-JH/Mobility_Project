import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Modal, View, Text, StyleSheet } from 'react-native';
import { SafeButton } from './SafeButton';
import { useEmergency } from '../context/EmergencyContext';
import { useTriggerEmergency } from '../hooks/useUserMutations';
import { userApi } from '../api/userApi';

const COUNTDOWN_SEC = 10;

export const GlobalEmergencyOverlay: React.FC = () => {
  const { emergencyState, dismissSOS } = useEmergency();
  const emergencyMutation = useTriggerEmergency();

  const [countdown, setCountdown] = useState(COUNTDOWN_SEC);
  const sentRef = useRef(false);

  // Keep latest emergency state accessible in stable callbacks without re-creating them
  const latestStateRef = useRef(emergencyState);
  useEffect(() => {
    latestStateRef.current = emergencyState;
  }, [emergencyState]);

  const sendSOS = useCallback(() => {
    if (sentRef.current) return;
    sentRef.current = true;
    const { reason } = latestStateRef.current;
    emergencyMutation.mutate(
      { reason: reason || 'Emergency SOS' },
      {
        onSuccess: () => dismissSOS(),
        onError: () => {
          // Keep overlay open for retry; allow re-send
          sentRef.current = false;
        },
      },
    );
  }, [emergencyMutation, dismissSOS]);

  const handleCancel = useCallback(() => {
    sentRef.current = false;
    // Best-effort false alarm report to server when emergency was server-originated
    const { emergencyId, source } = latestStateRef.current;
    if (source === 'server' && emergencyId) {
      userApi.acknowledgeEmergency(emergencyId, 'false_alarm').catch(() => {});
    }
    dismissSOS();
  }, [dismissSOS]);

  // Keep stable ref to sendSOS so countdown effect has no deps on it
  const sendSOSRef = useRef(sendSOS);
  useEffect(() => {
    sendSOSRef.current = sendSOS;
  }, [sendSOS]);

  // Reset when overlay opens
  useEffect(() => {
    if (!emergencyState.visible) return;
    setCountdown(COUNTDOWN_SEC);
    sentRef.current = false;
  }, [emergencyState.visible]);

  // Countdown tick — depends only on visible + countdown, NOT on sendSOS (avoids stale closure)
  useEffect(() => {
    if (!emergencyState.visible) return;
    if (countdown <= 0) {
      sendSOSRef.current();
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [emergencyState.visible, countdown]);

  const isServerEmergency = emergencyState.source === 'server';

  return (
    <Modal
      visible={emergencyState.visible}
      transparent
      animationType="fade"
      statusBarTranslucent
    >
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={[styles.countdownCircle, countdown <= 3 && styles.countdownUrgent]}>
            <Text style={styles.countdownText}>{countdown}</Text>
          </View>

          <Text style={styles.title}>Emergency SOS</Text>

          {isServerEmergency && (
            <View style={styles.sourceBadge}>
              <Text style={styles.sourceBadgeText}>DEVICE DETECTED INCIDENT</Text>
            </View>
          )}

          <Text style={styles.message}>
            {`Sending emergency signal in ${countdown} second${countdown !== 1 ? 's' : ''}...`}
          </Text>

          <View style={styles.buttons}>
            <SafeButton
              title="Cancel (False Alarm)"
              variant="secondary"
              onPress={handleCancel}
              style={styles.cancelBtn}
            />
            <SafeButton
              title={emergencyMutation.isPending ? 'Sending...' : 'Send Now'}
              variant="danger"
              onPress={sendSOS}
              disabled={emergencyMutation.isPending}
              style={styles.confirmBtn}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 28,
    alignItems: 'center',
    width: '100%',
    maxWidth: 420,
  },
  countdownCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#fee2e2',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 2,
    borderColor: '#ef4444',
  },
  countdownUrgent: {
    backgroundColor: '#ef4444',
    borderColor: '#b91c1c',
  },
  countdownText: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#ef4444',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 8,
  },
  sourceBadge: {
    backgroundColor: '#fef3c7',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#f59e0b',
  },
  sourceBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#92400e',
    letterSpacing: 0.5,
  },
  message: {
    fontSize: 15,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 28,
    lineHeight: 22,
  },
  buttons: {
    width: '100%',
    gap: 12,
  },
  cancelBtn: {
    width: '100%',
    backgroundColor: '#94a3b8',
  },
  confirmBtn: {
    width: '100%',
  },
});
