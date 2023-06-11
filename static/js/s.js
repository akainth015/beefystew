const {createApp} = Vue;

createApp({
    data() {
        return {
            file_name: null, // File name
            file_type: null, // File type
            file_date: null, // Date when file uploaded
            file_path: null, // Path of file in GCS
            file_size: null, // Size of uploaded file
            download_url: null, // URL to download a file
            uploading: false, // upload in progress
            deleting: false, // delete in progress
            delete_confirmation: false, // Show the delete confirmation thing.
            posts: [],
            index: 1,
            answer: '',
            results: [],
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
            console.log("file_info")
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
        set_result (r) {
            console.log("SET_RESULT")
            // Sets the results after a server call.
            file_name = r.data.file_name;
            file_type = r.data.file_type;
            file_date = r.data.file_date;
            file_path = r.data.file_path;
            file_size = r.data.file_size;
            download_url = r.data.download_url;
        },
        upload_file(event) {
            console.log("UPLOAD_FILE")
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
                    console.log("UPLOAD_FILE PROMISE")
                    let upload_url = response.data.signed_url
                    let file_path = response.data.file_path 
                    // var XMLHttpRequest = require("xmlhttprequest").XMLHttprequest;
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
            console.log("UPLOAD_COMPLETE")
            axios.post(notify_url, {
                file_name: file_name, 
                file_type: file_type,
                file_path: file_path,
                file_size: file_size,
            })
            .then(response => {
                console.log("UPLOAD_COMPLETE PROMISE")
                this.uploading = false;
                file_name = file_name;
                file_type = file_type;
                file_path = file_path;
                file_size = file_size;
                file_date = response.data.file_date;
                download_url = response.data.download_url;
                // console.log(file_name)
                // console.log(file_type)
                // console.log(file_path)
                // console.log(download_url)
            })
        },
        submit_answer() {
            (this.results).push({index: this.index, answer: this.answer});
            console.log(this.results);
            this.index = this.index + 1;
        },
    },
    computed: {
        file_info() {
            console.log("COMPUTED FILE_INFO")
            return this.file_info
        }
    },
    created() {
        console.log("HELLO THIS IS INIT")
        axios.get(file_info_url)
        .then(response => {
            console.log("INITIALIZATION")
            this.set_result(response);
        })
        axios.get(get_posts_url)
            .then((response) => {
                this.posts = response.data;
            });
    },
    
}).mount('#app');
