const {createApp} = Vue;

createApp({
    data() {
        return {
            lastPostSelectedForDwnl: null,
            uploading: false, // upload in progress
            posts: [],
            index: 1,
            answer: '',
            results: [],
            caption: customQuestion,
            imagePreview: "",
            selectedFile: null,
            submitButtonStatus: "Post"
        };
    },
    methods: {
        downloadSelectedImages() {

        },
        submit_answer() {
            (this.results).push({index: this.index, answer: this.answer});
            console.log(this.results);
            this.index = this.index + 1;
        },
        enumerate(a) {
            let k = 0;
            a.map((e) => {e._idx = k++;});
            return a;
        },
        humanFileSize(bytes, si=false, dp=1) {
            const thresh = si ? 1000 : 1024; 
            if (Math.abs(bytes) < thresh) {
                return bytes + ' B';
            }
            const units = si
            ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
            : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
        let u = -1;
        const r = 10**dp;
        
        do {
            bytes /= thresh;
            ++u;
        } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);
        
        return bytes.toFixed(dp) + ' ' + units[u];
        },

        file_info() {
            if (this.file_path) {
                let info = "";
                if (this.file_size) {
                    info = humanFileSize(this.file_size.toString(), si=true);
                }
                if (this.file_type) {
                    if (info) {
                        info += " " + this.file_type;
                    } else {
                        info = file_type
                    }
                }
                if (info) {
                    info = " (" + info + ")"
                }
                return file_name + info
            } else {
                return "";
            }
        },
        upload_file(event) {
            let file = this.selectedFile;
            if (file) {
                axios.postForm(classify_url, {
                    image: file
                })
                .then (response => {
                    const isDraft = response.data.result !== "Accepted";
                    this.uploading = true;
                    let file_type = file.type
                    let file_name = file.name
                    let file_size = file.size
                    axios.post(obtain_gcs_url, {
                        action: "PUT",
                        mimetype: file_type,
                        file_name: file_name
                    })
                        .then(response => {
                            let upload_url = response.data.signed_url
                            let file_path = response.data.file_path
                            var req = new XMLHttpRequest();
                            req.addEventListener("load",
                                () => this.upload_complete(file_name, file_type, file_size, file_path, isDraft)
                            );
                            req.open("PUT", upload_url, true)
                            req.send(file)
                        })
                });
            }
        },
        upload_complete (file_name, file_type, file_size, file_path, isDraft) {
            axios.post(notify_url, {
                file_path: file_path,
                is_draft: isDraft,
                caption: this.caption,
            })
            .then(response => {
                this.uploading = false;
                if (isDraft) {
                    window.alert("Your post was submitted as a draft for review by the almighty council.");
                }
                location.reload();
            })
        },
        onDwlCheckboxClick(post, event) {
            if (event.shiftKey && this.lastPostSelectedForDwnl !== null) {
                const lastPostIdx = this.posts.indexOf(this.lastPostSelectedForDwnl);
                const thisPostIdx = this.posts.indexOf(post);
                const start = lastPostIdx > thisPostIdx ? thisPostIdx : lastPostIdx;
                const end = lastPostIdx > thisPostIdx ? lastPostIdx : thisPostIdx;
                this.posts.slice(start, end).forEach((post) => {
                    post.selected = this.posts[lastPostIdx].selected;
                });
            }
            this.lastPostSelectedForDwnl = post;
        },
        approveDraft(post) {
            axios.post(approve_url, {
                postId: post.post.id
            })
                .then(response => post.post.draft = false);
        },
        updateImgPreview(event) {
            const selectedFile = event.target.files[0];

            this.submitButtonStatus = "Loading";
            axios.postForm(classify_url, {
                    image: selectedFile
            })
                .then(response => {
                    if (response.data.result === "Accepted") {
                        this.submitButtonStatus = "Post";
                    } else {
                        this.submitButtonStatus = "Request Approval";
                    }
                })
                .catch(() => {
                    location.assign(login_url + "?next=" + location.pathname.toString());
                });

            this.selectedFile = selectedFile;
            const fr = new FileReader();
            fr.onload = () => {
                this.imagePreview = fr.result;
            }
            fr.readAsDataURL(selectedFile);
        }


    },
    created() {
        axios.get(get_posts_url)
            .then((response) => {
                this.posts = response.data;
            });
    },
    
}).mount('#app');
