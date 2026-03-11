import { Pinecone } from '@pinecone-database/pinecone';
import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config({ path: '~/.openclaw/workspace-forge/.env' });

const pinecone = new Pinecone({ apiKey: process.env.PINECONE_API_KEY });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const INDEX_NAME = 'saimemory';
const NAMESPACE = 'longterm';

async function chunkText(text, chunkSize = 1000, overlap = 200) {
  const chunks = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.slice(start, end));
    start += chunkSize - overlap;
  }
  return chunks;
}

async function embedText(text) {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text
  });
  return response.data[0].embedding;
}

async function upsertMemory(filePath, namespace = NAMESPACE) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const fileName = path.basename(filePath);
  const chunks = await chunkText(content);
  
  console.log(`Processing ${fileName}: ${chunks.length} chunks`);
  
  const index = pinecone.index(INDEX_NAME);
  
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const embedding = await embedText(chunk);
    const id = `${fileName}-chunk-${i}`;
    
    await index.namespace(namespace).upsert([{
      id,
      values: embedding,
      metadata: {
        source: fileName,
        chunkIndex: i,
        text: chunk,
        timestamp: new Date().toISOString()
      }
    }]);
    
    process.stdout.write('.');
  }
  console.log(` Done!`);
}

async function main() {
  // Check if index exists
  const indexes = await pinecone.listIndexes();
  const indexExists = indexes.indexes?.some(i => i.name === INDEX_NAME);
  
  if (!indexExists) {
    console.log(`Creating index ${INDEX_NAME}...`);
    await pinecone.createIndex({
      name: INDEX_NAME,
      dimension: 1536,
      metric: 'cosine',
      spec: { serverless: { cloud: 'aws', region: 'us-east-1' } }
    });
    // Wait for index to be ready
    await new Promise(r => setTimeout(r, 30000));
  }
  
  // Process MEMORY.md
  const memoryPath = '~/.openclaw/workspace/MEMORY.md';
  if (fs.existsSync(memoryPath)) {
    await upsertMemory(memoryPath, 'longterm');
  }
  
  // Process daily memory files
  const memoryDir = '~/.openclaw/workspace/memory';
  if (fs.existsSync(memoryDir)) {
    const files = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md'));
    for (const file of files) {
      await upsertMemory(path.join(memoryDir, file), 'daily');
    }
  }
  
  console.log('\n✅ Memory uploaded to Pinecone!');
}

main().catch(console.error);
