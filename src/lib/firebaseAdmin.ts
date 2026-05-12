import admin from "firebase-admin";
import fs from "fs";
import path from "path";

const serviceAccountPath = path.join(process.cwd(), "config", "firebase_key.json");

if (!fs.existsSync(serviceAccountPath)) {
  throw new Error("config/firebase_key.json 파일이 없습니다.");
}

const serviceAccount = JSON.parse(fs.readFileSync(serviceAccountPath, "utf8"));

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    storageBucket: "jobpick.firebasestorage.app",
  });
}

const db = admin.firestore();
const bucket = admin.storage().bucket("jobpick.firebasestorage.app");

export { admin, db, bucket };