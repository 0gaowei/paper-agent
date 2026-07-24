import type {
  Paper,
  SearchSession,
  SearchStats,
  QueryUnderstanding,
  SubQuery,
  GraphData,
  HistoryRecord,
  ApiConfig,
  SearchConfig,
  DataSourceConfig
} from '@/types'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
const randomDelay = () => delay(500 + Math.random() * 1500)

// 模拟论文数据
const mockPapers: Paper[] = [
  {
    id: 'p1',
    title: 'Attention Is All You Need',
    authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit', 'Llion Jones', 'Aidan N. Gomez', 'Łukasz Kaiser', 'Illia Polosukhin'],
    year: 2017,
    venue: 'NeurIPS',
    abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    doi: '10.48550/arXiv.1706.03762',
    citationCount: 89234,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1706.03762',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Attention-Is-All-You-Need-Vaswani-Shazeer/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e0',
    relevance: 0.98,
    tags: ['transformer', 'attention', 'NLP', 'deep learning']
  },
  {
    id: 'p2',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    authors: ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
    year: 2018,
    venue: 'NAACL',
    abstract: 'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.',
    doi: '10.48550/arXiv.1810.04805',
    citationCount: 72341,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1810.04805',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/BERT-Pre-training-of-Deep-Bidirectional-Devlin-Chang/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e1',
    relevance: 0.95,
    tags: ['BERT', 'pre-training', 'NLP', 'transformer']
  },
  {
    id: 'p3',
    title: 'GPT-4 Technical Report',
    authors: ['OpenAI', 'Josh Achiam', 'Steven Adler', 'Sandipan Agarwal', 'Lama Ahmad'],
    year: 2023,
    journal: 'arXiv preprint',
    abstract: 'We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs. GPT-4 exhibits human-level performance on various professional and academic benchmarks.',
    doi: '10.48550/arXiv.2303.08774',
    citationCount: 12453,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2303.08774',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/GPT-4-Technical-Report-OpenAI/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e2',
    relevance: 0.92,
    tags: ['GPT-4', 'large language model', 'multimodal', 'AI']
  },
  {
    id: 'p4',
    title: 'Deep Residual Learning for Image Recognition',
    authors: ['Kaiming He', 'Xiangyu Zhang', 'Shaoqing Ren', 'Jian Sun'],
    year: 2016,
    venue: 'CVPR',
    abstract: 'Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.',
    doi: '10.1109/CVPR.2016.90',
    citationCount: 156789,
    isOpenAccess: false,
    pdfUrl: 'https://arxiv.org/pdf/1512.03385',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Deep-Residual-Learning-for-Image-Recognition-He-Zhang/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e3',
    relevance: 0.88,
    tags: ['ResNet', 'deep learning', 'computer vision', 'residual learning']
  },
  {
    id: 'p5',
    title: 'Generative Adversarial Networks',
    authors: ['Ian J. Goodfellow', 'Jean Pouget-Abadie', 'Mehdi Mirza', 'Bing Xu', 'David Warde-Farley', 'Sherjil Ozair', 'Aaron Courville', 'Yoshua Bengio'],
    year: 2014,
    venue: 'NeurIPS',
    abstract: 'We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models: a generative model G that captures the data distribution, and a discriminative model D that estimates the probability that a sample came from the training data rather than G.',
    doi: '10.48550/arXiv.1406.2661',
    citationCount: 67892,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1406.2661',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Generative-Adversarial-Networks-Goodfellow-Pouget-Abadie/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e4',
    relevance: 0.85,
    tags: ['GAN', 'generative model', 'deep learning', 'adversarial']
  },
  {
    id: 'p6',
    title: 'Language Models are Few-Shot Learners',
    authors: ['Tom B. Brown', 'Benjamin Mann', 'Nick Ryder', 'Melanie Subbiah'],
    year: 2020,
    venue: 'NeurIPS',
    abstract: 'Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples.',
    doi: '10.48550/arXiv.2005.14165',
    citationCount: 45678,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2005.14165',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Language-Models-are-Few-Shot-Learners-Brown-Mann/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e5',
    relevance: 0.93,
    tags: ['GPT-3', 'few-shot learning', 'language model', 'NLP']
  },
  {
    id: 'p7',
    title: 'ImageNet Classification with Deep Convolutional Neural Networks',
    authors: ['Alex Krizhevsky', 'Ilya Sutskever', 'Geoffrey E. Hinton'],
    year: 2012,
    venue: 'NeurIPS',
    abstract: 'We trained a large, deep convolutional neural network to classify the 1.2 million high-resolution images in the ImageNet LSVRC-2010 contest into the 1000 different classes. On the test data, we achieved top-1 and top-5 error rates of 37.5% and 17.0%.',
    doi: '10.1145/3065386',
    citationCount: 112345,
    isOpenAccess: false,
    pdfUrl: 'https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/ImageNet-Classification-with-Deep-Convolutional-Krizhevsky-Sutskever/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e6',
    relevance: 0.82,
    tags: ['AlexNet', 'ImageNet', 'CNN', 'computer vision']
  },
  {
    id: 'p8',
    title: 'Playing Atari with Deep Reinforcement Learning',
    authors: ['Volodymyr Mnih', 'Koray Kavukcuoglu', 'David Silver', 'Alex Graves', 'Ioannis Antonoglou'],
    year: 2013,
    venue: 'arXiv preprint',
    abstract: 'We present the first deep learning model to successfully learn control policies directly from high-dimensional sensory input using reinforcement learning. The model is a convolutional neural network, trained with a variant of Q-learning, whose input is raw pixels and whose output is a value function estimating future reward.',
    doi: '10.48550/arXiv.1312.5602',
    citationCount: 34567,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1312.5602',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Playing-Atari-with-Deep-Reinforcement-Learning-Mnih-Kavukcuoglu/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e7',
    relevance: 0.79,
    tags: ['deep reinforcement learning', 'DQN', 'Atari', 'RL']
  },
  {
    id: 'p9',
    title: 'Mastering the Game of Go with Deep Neural Networks and Tree Search',
    authors: ['David Silver', 'Aja Huang', 'Chris J. Maddison', 'Arthur Guez', 'Laurent Sifre'],
    year: 2016,
    journal: 'Nature',
    abstract: 'The game of Go has long been viewed as the most challenging of classic games for artificial intelligence owing to its enormous search space and the difficulty of evaluating board positions and moves. Here we introduce a new approach to computer Go that uses value networks to evaluate board positions and policy networks to select moves.',
    doi: '10.1038/nature16961',
    citationCount: 23456,
    isOpenAccess: false,
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Mastering-the-Game-of-Go-with-Deep-Neural-Networks-Silver-Huang/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e8',
    relevance: 0.76,
    tags: ['AlphaGo', 'Go', 'reinforcement learning', 'neural networks']
  },
  {
    id: 'p10',
    title: 'CLIP: Learning Transferable Visual Models From Natural Language Supervision',
    authors: ['Alec Radford', 'Jong Wook Kim', 'Chris Hallacy', 'Aditya Ramesh'],
    year: 2021,
    venue: 'ICML',
    abstract: 'State-of-the-art computer vision systems are trained to predict a fixed set of predetermined object categories. This restricted form of supervision limits their generality and usability since additional labeled data is needed to specify any other visual concept. Learning directly from raw text about images is a promising alternative.',
    doi: '10.48550/arXiv.2103.00020',
    citationCount: 28934,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2103.00020',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/CLIP-Learning-Transferable-Visual-Models-From-Radford-Kim/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e9',
    relevance: 0.91,
    tags: ['CLIP', 'vision-language', 'multimodal', 'transfer learning']
  },
  {
    id: 'p11',
    title: 'Denoising Diffusion Probabilistic Models',
    authors: ['Jonathan Ho', 'Ajay Jain', 'Pieter Abbeel'],
    year: 2020,
    venue: 'NeurIPS',
    abstract: 'We present high quality image synthesis results using diffusion probabilistic models, a class of latent variable models inspired by considerations from nonequilibrium thermodynamics. Our best results are obtained by training on a weighted variational bound designed according to a novel connection between diffusion probabilistic models and denoising score matching.',
    doi: '10.48550/arXiv.2006.11239',
    citationCount: 19234,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2006.11239',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Denoising-Diffusion-Probabilistic-Models-Ho-Jain/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e10',
    relevance: 0.89,
    tags: ['diffusion model', 'generative model', 'DDPM', 'image synthesis']
  },
  {
    id: 'p12',
    title: 'Word2Vec: Distributed Representations of Words and Phrases and their Compositionality',
    authors: ['Tomas Mikolov', 'Ilya Sutskever', 'Kai Chen', 'Greg Corrado', 'Jeffrey Dean'],
    year: 2013,
    venue: 'NeurIPS',
    abstract: 'The recently introduced Continuous Bag-of-Words model and the Skip-gram model are efficient methods for learning high-quality distributed vector representations from large amounts of unstructured text data. We present several extensions that improve both the quality of the vectors and the training speed.',
    doi: '10.48550/arXiv.1310.4546',
    citationCount: 45678,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1310.4546',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Word2Vec-Distributed-Representations-of-Words-and-Mikolov-Sutskever/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e11',
    relevance: 0.84,
    tags: ['word embeddings', 'Word2Vec', 'NLP', 'representation learning']
  },
  {
    id: 'p13',
    title: 'Stable Diffusion: A Text-to-Image Diffusion Model',
    authors: ['Robin Rombach', 'Andreas Blattmann', 'Dominik Lorenz', 'Patrick Esser', 'Björn Ommer'],
    year: 2022,
    venue: 'CVPR',
    abstract: 'We present a latent text-to-image diffusion model enabling synthesis of photo-realistic images conditioned on text descriptions. By crossing the bridge between conditional image generation and pretraining on large paired image-text data, our model achieves competitive quality while offering significant computational advantages.',
    doi: '10.48550/arXiv.2112.10741',
    citationCount: 15678,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2112.10741',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Stable-Diffusion-A-Text-to-Image-Diffusion-Model-Rombach-Blattmann/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e12',
    relevance: 0.94,
    tags: ['Stable Diffusion', 'text-to-image', 'diffusion model', 'generative AI']
  },
  {
    id: 'p14',
    title: 'Neural Machine Translation by Jointly Learning to Align and Translate',
    authors: ['Dzmitry Bahdanau', 'Kyunghyun Cho', 'Yoshua Bengio'],
    year: 2014,
    venue: 'ICLR',
    abstract: 'Neural machine translation is a recently proposed approach to machine translation. Unlike the traditional statistical machine translation, the neural machine translation aims at building a single neural network that can be jointly tuned to maximize the translation performance.',
    doi: '10.48550/arXiv.1409.0473',
    citationCount: 56789,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1409.0473',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Neural-Machine-Translation-by-Jointly-Learning-Bahdanau-Cho/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e13',
    relevance: 0.86,
    tags: ['attention mechanism', 'NMT', 'sequence-to-sequence', 'neural network']
  },
  {
    id: 'p15',
    title: 'Dropout: A Simple Way to Prevent Neural Networks from Overfitting',
    authors: ['Nitish Srivastava', 'Geoffrey Hinton', 'Alex Krizhevsky', 'Ilya Sutskever', 'Ruslan Salakhutdinov'],
    year: 2014,
    journal: 'JMLR',
    abstract: 'Deep neural networks with a large number of parameters are very powerful machine learning systems. However, overfitting is a serious problem in such networks. Dropout is a technique for addressing this problem. The key idea is to randomly drop units along with their connections during training.',
    doi: '10.5555/2627435.2670313',
    citationCount: 34567,
    isOpenAccess: true,
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Dropout-A-Simple-Way-to-Prevent-Neural-Networks-Srivastava-Hinton/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e14',
    relevance: 0.78,
    tags: ['dropout', 'regularization', 'overfitting', 'deep learning']
  },
  {
    id: 'p16',
    title: 'The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks',
    authors: ['Jonathan Frankle', 'Michael Carbin'],
    year: 2019,
    venue: 'ICLR',
    abstract: 'Neural network pruning research typically disconnects the pruning and training procedures, treating them as separate steps. The lottery ticket hypothesis suggests that for standard architectures, randomly initialized dense networks contain subnetworks that reach test accuracy comparable to the original network when trained in isolation.',
    doi: '10.48550/arXiv.1803.03635',
    citationCount: 8765,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/1803.03635',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/The-Lottery-Ticket-Hypothesis-Finding-Sparse-Frankle-Carbin/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e15',
    relevance: 0.72,
    tags: ['network pruning', 'lottery ticket hypothesis', 'sparse networks', 'neural network']
  },
  {
    id: 'p17',
    title: 'Segment Anything',
    authors: ['Alexander Kirillov', 'Eric Mintun', 'Nikhila Ravi', 'Hanzi Mao', 'Chloe Rolland'],
    year: 2023,
    venue: 'ICCV',
    abstract: 'We introduce the Segment Anything Model (SAM), a new image segmentation model with impressive zero-shot transfer capabilities. SAM can perform segmentation given various prompts in the style of interactive segmentation and can output all valid masks for an image efficiently.',
    doi: '10.48550/arXiv.2304.02643',
    citationCount: 9876,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2304.02643',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Segment-Anything-Kirillov-Mintun/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e16',
    relevance: 0.90,
    tags: ['SAM', 'segmentation', 'computer vision', 'foundation model']
  },
  {
    id: 'p18',
    title: 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale',
    authors: ['Alexey Dosovitskiy', 'Lucas Beyer', 'Alexander Kolesnikov', 'Dirk Weissenborn'],
    year: 2021,
    venue: 'ICLR',
    abstract: 'While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. Inspired by the Transformer scaling successes in NLP and masked autoencoder approaches, we propose a pure transformer model for image classification.',
    doi: '10.48550/arXiv.2010.11929',
    citationCount: 23456,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2010.11929',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/An-Image-is-Worth-16x16-Words-Transformers-for-Dosovitskiy-Beyer/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e17',
    relevance: 0.87,
    tags: ['ViT', 'Vision Transformer', 'image classification', 'transformer']
  },
  {
    id: 'p19',
    title: 'Llama 2: Open Foundation and Fine-Tuned Chat Models',
    authors: ['Hugo Touvron', 'Louis Martin', 'Kevin Stone', 'Peter Albert'],
    year: 2023,
    journal: 'arXiv preprint',
    abstract: 'We introduce LLaMA 2, a collection of foundation language models ranging from 7B to 70B parameters. We trained LLaMA 2 on over 2 trillion tokens of data, with most of the data and context length doubling compared to the first version of LLaMA.',
    doi: '10.48550/arXiv.2307.09288',
    citationCount: 7654,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2307.09288',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/Llama-2-Open-Foundation-and-Fine-Tuned-Chat-Touvron-Martin/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e18',
    relevance: 0.96,
    tags: ['LLaMA', 'open source', 'language model', 'chat model']
  },
  {
    id: 'p20',
    title: 'In-context Learning Emerges from Pretraining',
    authors: ['Yanda Chen', 'Weijia Shi', 'Chenguang Wang', 'Mike Lewis'],
    year: 2023,
    journal: 'arXiv preprint',
    abstract: 'We study how in-context learning emerges during language model pretraining. Our analysis reveals that in-context learning ability correlates with specific pretraining behaviors and that certain training data characteristics facilitate its development.',
    doi: '10.48550/arXiv.2310.07916',
    citationCount: 2345,
    isOpenAccess: true,
    pdfUrl: 'https://arxiv.org/pdf/2310.07916',
    semanticScholarUrl: 'https://www.semanticscholar.org/paper/In-context-Learning-Emerges-from-Pretraining-Chen-Shi/204e307329ce8c5e99cc28e8a7e0b2b0c3f7b5e19',
    relevance: 0.71,
    tags: ['in-context learning', 'few-shot', 'language model', 'pretraining']
  }
]

// 模拟搜索历史
const mockHistory: HistoryRecord[] = [
  {
    id: 'h1',
    query: 'transformer architecture in NLP',
    sessionId: 's1',
    paperCount: 156,
    duration: 12.5,
    cost: 0.45,
    createdAt: '2026-07-22T10:30:00Z'
  },
  {
    id: 'h2',
    query: 'diffusion models for image generation',
    sessionId: 's2',
    paperCount: 89,
    duration: 8.2,
    cost: 0.32,
    createdAt: '2026-07-21T15:45:00Z'
  },
  {
    id: 'h3',
    query: 'reinforcement learning from human feedback',
    sessionId: 's3',
    paperCount: 67,
    duration: 6.8,
    cost: 0.28,
    createdAt: '2026-07-20T09:20:00Z'
  },
  {
    id: 'h4',
    query: 'large language model training',
    sessionId: 's4',
    paperCount: 234,
    duration: 18.3,
    cost: 0.67,
    createdAt: '2026-07-19T14:10:00Z'
  },
  {
    id: 'h5',
    query: 'computer vision foundation models',
    sessionId: 's5',
    paperCount: 112,
    duration: 9.5,
    cost: 0.38,
    createdAt: '2026-07-18T11:00:00Z'
  }
]

// API 函数
export const searchPapers = async (query: string, _config?: any): Promise<SearchSession> => {
  await randomDelay()
  
  const sessionId = `s_${Date.now()}`
  const understanding: QueryUnderstanding = {
    originalQuery: query,
    entities: {
      topics: extractTopics(query),
      methods: extractMethods(query),
      datasets: [],
      domains: extractDomains(query)
    },
    intent: determineIntent(query),
    queryType: 'academic_search'
  }
  
  const subQueries: SubQuery[] = [
    { id: 'sq1', query: query, type: 'topic' },
    { id: 'sq2', query: `related methods: ${extractMethods(query).join(', ')}`, type: 'method' },
    { id: 'sq3', query: `recent advances in ${extractTopics(query)[0] || query}`, type: 'topic' }
  ]
  
  const filteredPapers = mockPapers.filter(p => {
    const queryLower = query.toLowerCase()
    return (
      p.title.toLowerCase().includes(queryLower) ||
      p.abstract?.toLowerCase().includes(queryLower) ||
      p.tags?.some(t => t.toLowerCase().includes(queryLower)) ||
      p.authors.some(a => a.toLowerCase().includes(queryLower))
    )
  })
  
  const relevantPapers = filteredPapers.length > 0 ? filteredPapers : mockPapers.slice(0, 8)
  
  const stats: SearchStats = {
    totalPapers: relevantPapers.length + Math.floor(Math.random() * 100),
    relevantPapers: relevantPapers.length,
    apiCalls: Math.floor(Math.random() * 5) + 3,
    tokenUsage: Math.floor(Math.random() * 5000) + 2000,
    cost: Math.random() * 0.5 + 0.1,
    duration: Math.random() * 15 + 5
  }
  
  return {
    id: sessionId,
    query,
    status: 'completed',
    understanding,
    subQueries,
    papers: relevantPapers,
    stats,
    createdAt: new Date().toISOString(),
    completedAt: new Date().toISOString()
  }
}

export const getPaperDetail = async (paperId: string): Promise<Paper | null> => {
  await randomDelay()
  return mockPapers.find(p => p.id === paperId) || null
}

export const getCitationGraph = async (_sessionId: string): Promise<GraphData> => {
  await randomDelay()
  
  const centerPaper = mockPapers[Math.floor(Math.random() * mockPapers.length)]
  const references = mockPapers.slice(0, 5).map((p) => ({
    ...p,
    id: `ref_${p.id}`,
    relevance: 0.7 + Math.random() * 0.25
  }))
  const citedBy = mockPapers.slice(5, 10).map((p) => ({
    ...p,
    id: `cited_${p.id}`,
    relevance: 0.6 + Math.random() * 0.3
  }))
  
  const nodes = [
    { id: centerPaper.id, title: centerPaper.title, type: 'center' as const, relevance: 1.0, year: centerPaper.year, citationCount: centerPaper.citationCount },
    ...references.map(p => ({ id: p.id, title: p.title, type: 'reference' as const, relevance: p.relevance, year: p.year, citationCount: p.citationCount })),
    ...citedBy.map(p => ({ id: p.id, title: p.title, type: 'citedBy' as const, relevance: p.relevance, year: p.year, citationCount: p.citationCount }))
  ]
  
  const edges: { source: string; target: string; type: 'cites' | 'citedBy' }[] = []
  references.forEach((r, _idx) => edges.push({ source: centerPaper.id, target: r.id, type: 'cites' as const }))
  citedBy.forEach((c, _idx) => edges.push({ source: c.id, target: centerPaper.id, type: 'citedBy' as const }))
  
  return { nodes, edges }
}

export const getSearchHistory = async (): Promise<HistoryRecord[]> => {
  await randomDelay()
  return mockHistory
}

export const getSettings = async (): Promise<{
  apiConfig: ApiConfig
  searchConfig: SearchConfig
  dataSources: DataSourceConfig[]
}> => {
  await randomDelay()
  return {
    apiConfig: {
      provider: 'openai',
      apiKey: '',
      baseUrl: '',
      model: 'gpt-4-turbo'
    },
    searchConfig: {
      enableQueryDecomposition: true,
      enableIterativeSearch: true,
      enableQueryRewrite: true,
      maxIterations: 3,
      maxResults: 100
    },
    dataSources: [
      { name: 'arXiv', enabled: true, priority: 1 },
      { name: 'Semantic Scholar', enabled: true, priority: 2 },
      { name: 'PubMed', enabled: false, priority: 3 },
      { name: 'IEEE Xplore', enabled: false, priority: 4 }
    ]
  }
}

export const saveSettings = async (_settings: any): Promise<{ success: boolean }> => {
  await randomDelay()
  return { success: true }
}

// 辅助函数
function extractTopics(query: string): string[] {
  const keywords = ['transformer', 'diffusion', 'reinforcement learning', 'neural network', 'language model', 'vision', 'GPT', 'BERT', 'attention', 'generative']
  return keywords.filter(k => query.toLowerCase().includes(k.toLowerCase()))
}

function extractMethods(query: string): string[] {
  const methods = ['attention', 'self-attention', 'gradient descent', 'backpropagation', 'fine-tuning', 'pre-training']
  return methods.filter(m => query.toLowerCase().includes(m.toLowerCase()))
}

function extractDomains(query: string): string[] {
  const domains: Record<string, string[]> = {
    'NLP': ['NLP', 'natural language', 'text', 'language'],
    'Computer Vision': ['vision', 'image', 'visual', 'imageNet'],
    'Reinforcement Learning': ['reinforcement', 'RL', 'agent', 'policy'],
    'Generative AI': ['generative', 'GAN', 'diffusion', 'synthesis']
  }
  
  return Object.entries(domains)
    .filter(([_, keywords]) => keywords.some(k => query.toLowerCase().includes(k.toLowerCase())))
    .map(([domain]) => domain)
}

function determineIntent(query: string): 'survey' | 'specific' | 'comparative' | 'methodology' {
  if (query.toLowerCase().includes('compare') || query.toLowerCase().includes('versus')) return 'comparative'
  if (query.toLowerCase().includes('method') || query.toLowerCase().includes('technique')) return 'methodology'
  if (query.toLowerCase().includes('survey') || query.toLowerCase().includes('overview')) return 'survey'
  return 'specific'
}

// 导出模拟数据供组件使用
export { mockPapers, mockHistory }
