import os
import wave
import math
import struct

def generate_bell_sound(file_path="assets/sounds/bell.wav"):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    sample_rate = 44100  # 44.1kHz (Qualidade de áudio padrão)
    duration = 0.8        # Duração em segundos
    frequency = 880.0     # Frequência da nota (Lá / A5)
    
    num_samples = int(sample_rate * duration)
    
    with wave.open(file_path, 'w') as wav_file:
        # Configurações do arquivo WAV (1 canal Mono, 2 bytes por amostra, 44100Hz)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Decaimento exponencial para simular a ressonância de um sino
            decay = math.exp(-3.5 * t)
            
            # Onda senoidal com harmônico leve
            sine_wave = math.sin(2 * math.pi * frequency * t) + 0.3 * math.sin(2 * math.pi * (frequency * 2) * t)
            amplitude = int(32767 * 0.5 * sine_wave * decay)
            
            # Garante que os limites de 16-bit sejam respeitados
            amplitude = max(-32768, min(32767, amplitude))
            wav_file.writeframes(struct.pack('<h', amplitude))

    print(f"✅ Arquivo WAV de teste criado com sucesso em: {file_path}")

if __name__ == "__main__":
    generate_bell_sound()