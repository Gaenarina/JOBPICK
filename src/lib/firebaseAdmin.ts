import admin from "firebase-admin";
import fs from "fs";
import path from "path";

let serviceAccount;

// 1. 버셀(Vercel) 환경 변수가 등록되어 있는지 먼저 확인합니다.
if (process.env.FIREBASE_SERVICE_ACCOUNT) {
  serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
} else {
  // 2. 환경 변수가 없다면 (내 컴퓨터 로컬 환경이라면) 기존처럼 파일을 읽습니다.
  const serviceAccountPath = path.join(process.cwd(), "config", "firebase_key.json");

  if (!fs.existsSync(serviceAccountPath)) {
    throw new Error("config/firebase_key.json 파일이 없습니다. 로컬 환경이라면 파일을 확인하시고, Vercel 환경이라면 환경변수 설정을 확인하세요.");
  }

  serviceAccount = JSON.parse(fs.readFileSync(serviceAccountPath, "utf8"));
}

// 3. 파이어베이스 앱 초기화
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    storageBucket: "jobpick.firebasestorage.app",
  });
}

const db = admin.firestore();
const bucket = admin.storage().bucket("jobpick.firebasestorage.app");

export { admin, db, bucket };