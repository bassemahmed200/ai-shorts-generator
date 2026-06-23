document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('jobForm');
    const startBtn = document.getElementById('startBtn');
    const uploadSection = document.getElementById('uploadSection');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadBar = document.getElementById('uploadBar');
    const uploadPercent = document.getElementById('uploadPercent');
    
    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    const progressPercent = document.getElementById('progressPercent');
    const errorText = document.getElementById('errorText');
    
    const resultsSection = document.getElementById('resultsSection');
    const clipsGrid = document.getElementById('clipsGrid');
    const clipCardTemplate = document.getElementById('clipCardTemplate');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const videoUrl = document.getElementById('videoUrl').value;
        const videoFile = document.getElementById('videoFile').files[0];
        
        if (!videoUrl && !videoFile) {
            alert('Please provide a video URL or upload a file.');
            return;
        }

        // Prepare UI
        startBtn.disabled = true;
        startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        startBtn.innerHTML = '<span class="animate-pulse">Processing...</span>';
        
        progressSection.classList.add('hidden');
        resultsSection.classList.add('hidden');
        errorText.classList.add('hidden');
        clipsGrid.innerHTML = '';
        
        updateProgress('Starting job...', 0);

        try {
            let fileKey = null;
            
            // If file is selected, upload to R2 first
            if (videoFile) {
                updateUploadProgress('Preparing upload...', 0);
                uploadSection.classList.remove('hidden');
                
                // Get presigned URL
                const urlResponse = await fetch(
                    `/api/upload-url?filename=${encodeURIComponent(videoFile.name)}&content_type=${encodeURIComponent(videoFile.type || 'video/mp4')}`
                );
                
                if (!urlResponse.ok) {
                    const err = await urlResponse.json();
                    throw new Error(err.detail || 'Failed to get upload URL');
                }
                
                const { upload_url, file_key } = await urlResponse.json();
                fileKey = file_key;
                
                // Upload directly to R2
                await uploadToR2(upload_url, videoFile);
                
                uploadSection.classList.add('hidden');
            }
            
            // Create job
            const formData = new FormData();
            if (videoUrl) {
                formData.append('video_url', videoUrl);
            }
            if (fileKey) {
                formData.append('file_key', fileKey);
            }
            
            // Add other form fields
            formData.append('transcription_method', document.querySelector('[name="transcription_method"]').value);
            formData.append('analysis_provider', document.querySelector('[name="analysis_provider"]').value);
            formData.append('num_clips', document.querySelector('[name="num_clips"]').value);
            formData.append('clip_duration', document.querySelector('[name="clip_duration"]').value);
            formData.append('crop_style', document.querySelector('[name="crop_style"]').value);

            const response = await fetch('/api/jobs', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start job.');
            }

            const data = await response.json();
            const jobId = data.job_id;
            
            // Start polling
            pollJobStatus(jobId);
            
        } catch (error) {
            showError(error.message);
            resetBtn();
            uploadSection.classList.add('hidden');
        }
    });

    async function uploadToR2(uploadUrl, file) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
                    const totalMB = (e.total / (1024 * 1024)).toFixed(1);
                    updateUploadProgress(`Uploading ${loadedMB}MB / ${totalMB}MB`, percent);
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve();
                } else {
                    reject(new Error(`Upload failed: ${xhr.statusText}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed. Check your connection.'));
            });
            
            xhr.open('PUT', uploadUrl);
            xhr.setRequestHeader('Content-Type', file.type || 'video/mp4');
            xhr.send(file);
        });
    }

    function updateUploadProgress(text, percent) {
        uploadBar.style.width = `${percent}%`;
        uploadPercent.textContent = `${Math.round(percent)}%`;
        document.getElementById('uploadStatus').textContent = text;
    }

    async function pollJobStatus(jobId) {
        let pollCount = 0;
        const interval = setInterval(async () => {
            pollCount++;
            try {
                const response = await fetch(`/api/jobs/${jobId}`);
                
                if (response.status === 404) {
                    clearInterval(interval);
                    showError('Job not found. The server may have restarted. Please try again.');
                    resetBtn();
                    return;
                }
                
                if (!response.ok) throw new Error('Failed to fetch job status');
                
                const job = await response.json();
                
                const statusMap = {
                    'pending': 'Queued...',
                    'downloading': 'Downloading / Loading Video...',
                    'extracting_audio': 'Extracting Audio...',
                    'transcribing': 'Transcribing Audio to Text (AI)...',
                    'analyzing': 'Analyzing Transcript for Viral Moments (AI)...',
                    'generating_hooks': 'Generating Viral Hooks (AI)...',
                    'cutting': 'Cutting & Editing Clips (FFmpeg)...',
                    'done': 'Finished!',
                    'failed': 'Failed!'
                };

                updateProgress(statusMap[job.status] || job.status, job.progress);

                if (job.status === 'done') {
                    clearInterval(interval);
                    renderClips(job.result);
                    resetBtn();
                } else if (job.status === 'failed') {
                    clearInterval(interval);
                    showError(job.error || 'Unknown error occurred.');
                    resetBtn();
                }

            } catch (error) {
                console.error(error);
            }
        }, 2000);
    }

    function updateProgress(text, percent) {
        statusText.textContent = text;
        progressBar.style.width = `${percent}%`;
        progressPercent.textContent = `${Math.round(percent)}%`;
    }

    function showError(message) {
        errorText.textContent = message;
        errorText.classList.remove('hidden');
        statusText.textContent = 'Error';
        progressBar.classList.remove('from-purple-500', 'to-pink-500');
        progressBar.classList.add('bg-red-500');
    }

    function resetBtn() {
        startBtn.disabled = false;
        startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        startBtn.innerHTML = 'Generate Viral Shorts 🚀';
    }

    function renderClips(clips) {
        if (!clips || clips.length === 0) {
            clipsGrid.innerHTML = '<p class="col-span-full text-center text-gray-400">No clips were generated.</p>';
        } else {
            clips.forEach(clip => {
                const clone = clipCardTemplate.content.cloneNode(true);
                
                clone.querySelector('video').src = clip.download_url;
                clone.querySelector('.clip-title').textContent = clip.title;
                clone.querySelector('.clip-score').textContent = `Virality Score: ${clip.score}/10`;
                clone.querySelector('.clip-reason').textContent = clip.reason;
                
                const hooksList = clone.querySelector('.hooks-list');
                if (clip.hooks && clip.hooks.length > 0) {
                    clip.hooks.forEach(hook => {
                        const hookEl = document.createElement('div');
                        hookEl.className = 'bg-gray-700 rounded-lg p-2 border border-gray-600';
                        hookEl.innerHTML = `
                            <p class="text-white text-sm">${hook.hook}</p>
                            <span class="text-xs text-purple-300 uppercase">${hook.type.replace('_', ' ')}</span>
                        `;
                        hooksList.appendChild(hookEl);
                    });
                }
                
                const dlBtn = clone.querySelector('.clip-download');
                dlBtn.href = clip.download_url;
                
                clipsGrid.appendChild(clone);
            });
        }
        resultsSection.classList.remove('hidden');
    }
});
