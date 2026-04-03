# Keystroke Biometric Authentication System

## Overview

Keystroke-SaaS is a sophisticated biometric authentication platform that leverages deep learning to verify user identity based on keystroke dynamics. Rather than relying solely on traditional passwords, this system analyzes the unique patterns in how users type—including hold times, flight times, and typing rhythm—to establish a behavioral biometric signature.

The system implements a Transformer-based neural network trained on keystroke data from the Aalto University Keystroke Dataset, achieving high accuracy in user authentication while maintaining computational efficiency for real-time deployment.

## Key Features

**Behavioral Biometrics**: Captures and analyzes 30-keystroke sequences to extract timing patterns unique to each user, creating a behavioral signature that's difficult to forge.

**Transformer-Based Deep Learning**: Implements a multi-head attention mechanism to identify complex temporal dependencies in keystroke patterns, outperforming traditional statistical approaches.

**Real-Time Verification**: FastAPI backend provides sub-millisecond authentication verification with support for concurrent user sessions.

**Scalable Architecture**: MongoDB-backed session management enables horizontal scaling for enterprise deployments while maintaining detailed audit trails.

**Adaptive Thresholding**: Hybrid scoring system combining embedding-based similarity (80%) with statistical analysis (20%) to balance security and usability across diverse user populations.

**Enhanced Security**: Rate limiting, login attempt lockout, and secure token management prevent brute-force attacks and unauthorized access.

## Technical Architecture

### Backend
- **Framework**: FastAPI with async support for high-throughput request handling
- **Database**: MongoDB for user profiles, session logs, and security alerts
- **Model Runtime**: PyTorch with CPU/GPU acceleration support
- **Authentication**: JWT-based token system with configurable TTL and secure refresh mechanisms
- **Data Validation**: Pydantic models for strict input validation and type safety

### Frontend
- **Framework**: React with client-side routing for seamless navigation
- **Components**: Modular, reusable UI components for enrollment, authentication, and dashboard views
- **Styling**: Tailwind CSS for responsive, production-grade design
- **State Management**: Built for integration with modern state management solutions

### Machine Learning Pipeline
- **Dataset**: Aalto University Keystroke Dataset (136M+ keystroke events)
- **Data Processing**: Python notebooks for feature engineering including hold time, flight time, and sequence extraction
- **Model Architecture**: Custom Transformer encoder with multi-head attention (8+ heads), multiple stacked layers for deep temporal reasoning
- **Training Framework**: PyTorch with optimization techniques for efficient convergence

## Model Performance

The trained Transformer model demonstrates strong generalization across user populations:

### Confusion Matrix
![Confusion Matrix](results/confusion_matrix.png)
The model achieves low false positive rates critical for security-sensitive applications, while maintaining acceptable false negative rates for user experience.

### Model Comparison
![Model Comparison](results/comparison_chart.png)
Comparative analysis shows the Transformer model outperforms baseline approaches including statistical methods and shallow neural networks in both accuracy and robustness.

### User Distribution
![User Distribution](results/user_distribution.png)
The system validates performance across the top 50 most active users in the dataset, ensuring reliability for diverse typing profiles and patterns.

## Dataset

This project uses the **Aalto University Keystroke Dataset**, a comprehensive collection of keystroke dynamics research data:

**Source**: https://userinterfaces.aalto.fi/136Mkeystrokes/

This academic dataset provides authentic keystroke timing data collected from real users, enabling rigorous validation of biometric authentication accuracy and robustness across different populations and typing styles.

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 14+
- MongoDB instance (local or cloud-hosted)
- CUDA compatible GPU (optional, for faster model inference)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Configuration
Create a `.env` file in the backend directory with the following variables:

```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=YourApp
DB_NAME=keystroke_saas
MODEL_PATH=../models/transformer_model.pth
MEAN_PATH=../models/mean.npy
STD_PATH=../models/std.npy
TOKEN_SECRET=your-secret-key-change-in-production
TOKEN_TTL_MINUTES=120
CORS_ORIGINS=http://localhost:3000
```

## Authentication Flow

1. **Enrollment Phase**: User creates account and completes 3+ enrollment sessions minimum, each with 20+ keystroke observations
2. **Profile Building**: System extracts timing features and generates behavioral embedding using the Transformer model
3. **Authentication**: On login, keystroke sequence is encoded and compared against stored profile using hybrid scoring
4. **Decision**: Similarity score evaluated against adaptive threshold (0.80-0.85) for accept/reject decision
5. **Logging**: All authentication attempts logged with scores and decisions for anomaly detection and audit trails

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration with keystroke enrollment
- `POST /api/auth/login` - Keystroke-based authentication
- `POST /api/auth/enroll` - Additional enrollment sessions for profile strengthening
- `POST /api/auth/refresh` - Token refresh without re-keystroke verification

### User Management
- `GET /api/users/{username}` - Retrieve user profile and statistics
- `POST /api/users/{username}/sessions` - View authentication history
- `GET /api/users/{username}/alerts` - Security alerts and anomaly detections

## Model Architecture Details

The Transformer model processes keystroke sequences through:

1. **Input Embedding**: 30-keystroke sequences encoded with timing features (hold time, flight time)
2. **Multi-Head Attention**: 8+ attention heads capturing different temporal patterns simultaneously
3. **Positional Encoding**: Preserves sequence order information critical for timing-based features
4. **Transformer Encoder Layers**: Multiple stacked layers (4+) for deep feature learning
5. **Classification Head**: Final linear layer producing user probability scores across all enrolled users

This architecture captures long-range dependencies in typing behavior that simpler models miss, enabling robust authentication even as users' typing naturally evolves over time.

## Production Considerations

**Security**: Token secrets, database credentials, and model paths should be managed through environment variables or secure vaults in production.

**Scalability**: The system supports horizontal scaling with stateless API servers and a shared MongoDB backend.

**Monitoring**: Implement application performance monitoring and anomaly detection on failing authentication rates per user.

**Model Updates**: Periodic model retraining with new data maintains performance as user typing patterns naturally drift over extended periods.

**Privacy**: Keystroke timing data should be treated as biometric information under GDPR, CCPA, and similar regulations.

## Development & Testing

Run the test suite:
```bash
cd backend
pytest tests/
```

The test suite covers API endpoints, model inference, and database operations to ensure reliability in production environments.

## Future Enhancements

- Multi-modal biometric fusion combining keystroke dynamics with other behavioral signals
- Continuous authentication during active sessions without periodic re-verification
- Explainable AI interpretability layer to visualize which keystroke patterns drive authentication decisions
- Mobile platform support with touch-based typing pattern analysis
- Federated learning capabilities for training on distributed user data while preserving privacy

## Contributing

This project was developed as a comprehensive exploration of applying modern deep learning techniques to behavioral biometrics. Contributions, insights, and feedback from the security and machine learning communities are welcome.

## License

This project uses the Aalto University Keystroke Dataset under their research terms. Ensure compliance with dataset licensing before any commercial deployment.

## Contact & Information

For questions regarding the model, architecture, or implementation details, refer to the project documentation or existing issue threads. The codebase is structured to facilitate understanding of both the machine learning pipeline and the production-ready authentication system.

---

**Built with FastAPI, React, PyTorch, and MongoDB—demonstrating end-to-end ownership of a full-stack ML system from data pipeline through production deployment.**
