const {createApp} = Vue;

createApp({
    data() {
        return {
            uploading: false, // upload in progress
            posts: [],
        }
    },
    
    methods: {
        downloadSelectedImages() {
            window.alert("You've been pranked! The download doesn't work today");
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
                if (this.file_date) {
                    info += ", uploaded oogabooga seconds ago idk"
                }
                return file_name + info
            } else {
                return "";
            }
        },
        upload_file(event) {
            let input = event.target;
            let file = input.files[0]
            if (file) {
                this.uploading = true;
                let file_type = file.type
                let file_name = file.name 
                let file_size = file.size 
                axios.post(obtain_gcs_url, {
                    action: "PUT",
                    mimetype: file_type,
                    file_name: file_name
                })
                .then (response => {
                    let upload_url = response.data.signed_url
                    let file_path = response.data.file_path 
                    var req = new XMLHttpRequest();
                    req.addEventListener("load",
                        () => this.upload_complete(file_name, file_type, file_size, file_path)
                    );
                    req.open("PUT", upload_url, true)
                    req.send(file)
                })
            }
        },
        upload_complete (file_name, file_type, file_size, file_path) {
            axios.post(notify_url, {
                file_path: file_path,
            })
            .then(response => {
                this.uploading = false;
            })
        }


    },
    created() {
        axios.get(get_posts_url)
            .then((response) => {
                this.posts = response.data;
            });
    },
    
}).mount('#app');
