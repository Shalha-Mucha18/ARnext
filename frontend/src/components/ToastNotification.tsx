
import React, { useEffect, useState } from 'react';

interface ToastNotificationProps {
    message: string;
    type?: 'info' | 'warning' | 'error' | 'success';
    onClose: () => void;
    duration?: number;
}

const ToastNotification: React.FC<ToastNotificationProps> = ({
    message,
    type = 'warning',
    onClose,
    duration = 4000
}) => {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false);
            setTimeout(onClose, 300); // Wait for fade out animation
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    if (!message) return null;

    const bgColor = {
        info: '#3b82f6',
        warning: '#f59e0b',
        error: '#ef4444',
        success: '#10b981'
    }[type];

    const icon = {
        info: 'ℹ️',
        warning: '⚠️',
        error: '❌',
        success: '✅'
    }[type];

    return (
        <div
            style={{
                position: 'fixed',
                bottom: '24px',
                right: '24px',
                background: 'white',
                borderLeft: `4px solid ${bgColor}`,
                padding: '16px 24px',
                borderRadius: '8px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                zIndex: 9999,
                transition: 'all 0.3s ease-in-out',
                opacity: isVisible ? 1 : 0,
                transform: isVisible ? 'translateY(0)' : 'translateY(20px)'
            }}
        >
            <span style={{ fontSize: '1.25rem' }}>{icon}</span>
            <div>
                <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#1e293b' }}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                </h4>
                <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: '#64748b' }}>
                    {message}
                </p>
            </div>
            <button
                onClick={() => { setIsVisible(false); setTimeout(onClose, 300); }}
                style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    padding: '4px',
                    marginLeft: '12px',
                    fontSize: '1.25rem',
                    lineHeight: 1
                }}
            >
                ×
            </button>
        </div>
    );
};

export default ToastNotification;
