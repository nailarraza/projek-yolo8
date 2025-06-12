-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jun 11, 2025 at 12:10 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_projek_yolo8`
--

-- --------------------------------------------------------

--
-- Table structure for table `alembic_version`
--

CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `alembic_version`
--

INSERT INTO `alembic_version` (`version_num`) VALUES
('6d93008c9fe3');

-- --------------------------------------------------------

--
-- Table structure for table `detections`
--

CREATE TABLE `detections` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `image_name` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `detection_class` varchar(100) DEFAULT NULL,
  `confidence_score` float DEFAULT NULL,
  `generative_description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `detections`
--

INSERT INTO `detections` (`id`, `user_id`, `timestamp`, `image_name`, `image_path`, `detection_class`, `confidence_score`, `generative_description`) VALUES
(113, 1, '2025-06-08 02:04:34', 'capture_1_20250608_090434_annotated.jpg', 'uploads\\capture_1_20250608_090434_annotated.jpg', 'Tidak Terdeteksi', 0, 'Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan.'),
(114, 1, '2025-06-08 02:15:29', 'capture_1_20250608_091517_annotated.jpg', 'uploads/capture_1_20250608_091517_annotated.jpg', 'oli_bekas_tidak_layak', 39.08, 'Gagal menghasilkan deskripsi dari Gemini: 404 Gemini 1.0 Pro Vision has been deprecated on July 12, 2024. Consider switching to different model, for example gemini-1.5-flash.'),
(116, 1, '2025-06-08 02:26:42', 'capture_1_20250608_092622_annotated.jpg', 'uploads/capture_1_20250608_092622_annotated.jpg', 'oli_bekas_tidak_layak', 63.46, 'Gambar yang diberikan sangat buram dan tidak memberikan detail yang cukup untuk menilai kualitas oli sepeda motor secara akurat. Identifikasi model deteksi objek sebagai \'oli_bekas_tidak_layak\' mungkin benar, tetapi tanpa visual yang jelas, penilaian ini hanya bersifat spekulatif.  Untuk menganalisis kualitas oli, diperlukan gambar yang lebih jelas dan berkualitas yang menunjukkan warna, konsistensi, dan adanya kontaminan dalam oli tersebut.\n\n**Namun, mengingat identifikasi model dan kualitas gambar yang buruk, berikut beberapa kemungkinan kondisi oli dan rekomendasi:**\n\n**Kemungkinan Kondisi Oli Berdasarkan Identifikasi Model:**\n\n* **Warna gelap/hitam:**  Oli bekas yang sudah digunakan lama biasanya berubah warna menjadi lebih gelap, bahkan hitam.  Ini menunjukkan adanya partikel-partikel karbon dan logam yang terakumulasi akibat gesekan mesin.  Semakin gelap warnanya, semakin besar kemungkinan oli tersebut sudah terdegradasi dan kehilangan kemampuan pelumasnya.\n* **Konsistensi kental/encer:** Degradasi oli dapat menyebabkan perubahan konsistensi. Oli yang terlalu kental dapat menyebabkan kesulitan pelumasan dan peningkatan gesekan, sedangkan oli yang terlalu encer mungkin tidak memberikan perlindungan yang cukup pada komponen mesin.  Kualitas gambar tidak memungkinkan untuk menilai konsistensi.\n* **Adanya kontaminan:** Partikel-partikel logam, debu, atau air dapat tercampur dalam oli, mengurangi kualitas pelumasan dan merusak komponen mesin.  Ini juga tidak dapat dinilai dari gambar.\n* **Bau tidak sedap:** Oli bekas sering kali memiliki bau yang khas, dan bau yang menyimpang dapat mengindikasikan adanya masalah. Hal ini juga tidak dapat dinilai dari gambar.\n\n**Rekomendasi Perawatan atau Penggantian Oli:**\n\nKarena gambar tidak memberikan informasi yang cukup, rekomendasi terbaik adalah:\n\n* **Ganti oli segera:**  Jika model deteksi objek mengidentifikasi oli sebagai \"tidak layak pakai\", penggantian oli adalah langkah yang tepat untuk mencegah kerusakan pada mesin.  Jangan menggunakan kembali oli yang diduga sudah tidak layak pakai.\n* **Gunakan oli yang sesuai spesifikasi:**  Pilih oli dengan viskositas dan spesifikasi yang direkomendasikan oleh pabrikan sepeda motor Anda.  Ini biasanya tertera dalam buku panduan pemilik.\n* **Ganti filter oli:**  Filter oli yang kotor harus diganti bersamaan dengan oli baru. Filter oli berperan penting dalam menyaring kontaminan dari oli.\n* **Periksa secara teratur:**  Lakukan pemeriksaan berkala terhadap kondisi oli dan tingkat oli pada sepeda motor.  Periksa warna, bau, dan konsistensi oli, dan perhatikan adanya kebocoran.\n\n**Saran Umum Terkait Penggunaan Oli:**\n\n* **Ganti oli secara berkala:** Ikuti jadwal penggantian oli yang direkomendasikan oleh pabrikan sepeda motor.\n* **Panaskan mesin sebelum berkendara:**  Membiarkan mesin sedikit panas sebelum berkendara dapat membantu oli menyebar merata ke seluruh komponen mesin.\n* **Hindari penggunaan oli yang sudah kedaluwarsa:** Oli yang sudah kedaluwarsa dapat kehilangan kualitas pelumasnya dan dapat menyebabkan kerusakan pada mesin.\n* **Jangan mencampur oli dari merek atau jenis yang berbeda:**  Mencampur oli yang berbeda dapat menyebabkan reaksi kimia yang tidak diinginkan dan mengurangi kualitas pelumas.\n\n\n**Kesimpulan:**\n\nGambar yang diberikan tidak cukup informatif untuk analisis detail. Untuk mendapatkan penilaian yang akurat mengenai kondisi oli, diperlukan gambar yang lebih jelas.  Namun, jika model deteksi objek sudah mengklasifikasikannya sebagai \"oli_bekas_tidak_layak\", segera ganti oli dan filter oli dengan yang baru sesuai dengan spesifikasi pabrikan.  Lakukan pemeriksaan berkala untuk mencegah kerusakan mesin di masa mendatang.\n'),
(117, 1, '2025-06-08 02:28:38', 'capture_1_20250608_092822_annotated.jpg', 'uploads/capture_1_20250608_092822_annotated.jpg', 'oli_bekas_tidak_layak', 42.97, 'Gambar yang diberikan sangat buram dan tidak memungkinkan untuk menganalisis kondisi oli sepeda motor secara akurat.  Identifikasi \'oli_bekas_tidak_layak\' oleh model deteksi objek mungkin benar secara umum, tetapi tanpa gambar yang jelas, tidak dapat dipastikan.  Kualitas oli yang tidak layak biasanya ditandai dengan warna gelap, konsistensi kental, atau adanya partikel kotoran.\n\nUntuk memastikan kondisi oli, dibutuhkan pemeriksaan visual yang lebih detail, termasuk pengecekan warna, kekentalan, dan keberadaan kontaminan.  Jika oli memang sudah tidak layak pakai, segera lakukan penggantian oli dengan oli baru yang sesuai spesifikasi pabrikan sepeda motor. Gunakan filter oli baru saat penggantian.\n\nPerawatan rutin seperti penggantian oli sesuai jadwal yang dianjurkan (biasanya setiap 2000-4000 km, tergantung jenis oli dan penggunaan) sangat penting untuk menjaga performa mesin dan umur pakainya.  Hindari menggunakan oli yang sudah melewati masa pakai untuk mencegah kerusakan mesin yang lebih serius.\n'),
(118, 1, '2025-06-08 02:39:04', 'capture_1_20250608_093850_annotated.jpg', 'uploads/capture_1_20250608_093850_annotated.jpg', 'oli_bekas_tidak_layak', 57.32, 'Gambar yang diberikan sangat buram dan tidak memungkinkan untuk menganalisis kondisi oli secara visual.  Identifikasi model \"oli_bekas_tidak_layak\" tanpa visual yang jelas hanya dapat diandalkan jika model tersebut telah dilatih dengan data yang akurat dan komprehensif.  Oleh karena itu, kesimpulan tentang kualitas oli berdasarkan gambar ini tidak dapat dipertanggungjawabkan.\n\n\nUntuk memastikan kualitas oli dan kinerja mesin yang optimal, penggantian oli secara berkala sesuai rekomendasi pabrikan sangat penting.  Perhatikan warna, bau, dan konsistensi oli saat penggantian.  Oli yang kotor, berwarna gelap, berbau terbakar, atau terlalu kental mengindikasikan perlunya penggantian.\n\n\nSebagai saran umum, selalu gunakan oli yang sesuai dengan spesifikasi mesin sepeda motor Anda.  Hindari menggunakan oli yang sudah lewat masa pakai atau telah terkontaminasi.  Lakukan perawatan rutin termasuk pemeriksaan tingkat oli dan filter oli secara teratur untuk menjaga performa mesin dan memperpanjang umur pakainya.\n'),
(119, 1, '2025-06-08 04:07:56', 'capture_1_20250608_110739_annotated.jpg', 'uploads/capture_1_20250608_110739_annotated.jpg', 'oli_palsu', 44.46, 'Gambar menunjukkan tiga sampel oli dengan warna yang berbeda.  Identifikasi \"oli_palsu\" mengindikasikan adanya ketidaksesuaian kualitas.  Oli berwarna gelap (kemungkinan yang paling kanan) menunjukkan tingkat kontaminasi yang tinggi, mungkin akibat penggunaan yang terlalu lama atau adanya kotoran di dalam mesin. Oli berwarna lebih terang menunjukkan kualitas yang lebih baik, tetapi perlu dipertimbangkan juga viskositas dan kandungan aditifnya.  Warna yang tidak seragam menunjukkan kemungkinan ketidakmurnian atau campuran oli yang berbeda.\n\nRekomendasi perawatan adalah segera mengganti oli sepeda motor dengan oli yang sesuai spesifikasi pabrikan.  Pembersihan sistem pelumasan juga direkomendasikan untuk menghilangkan kontaminan.  Periksa secara berkala kondisi oli dan  gantilah sesuai jadwal perawatan yang dianjurkan. Menggunakan oli palsu dapat menyebabkan kerusakan mesin yang parah dan biaya perbaikan yang tinggi.\n\nUntuk menjaga performa mesin, selalu gunakan oli yang direkomendasikan pabrikan sepeda motor.  Hindari membeli oli dari sumber yang tidak terpercaya.  Pantau secara teratur warna dan kondisi oli.  Jika terlihat abnormal (seperti sangat gelap atau bercampur dengan partikel), segera lakukan penggantian.  Perawatan rutin mesin juga sangat penting untuk menjaga keawetannya.\n'),
(120, 1, '2025-06-08 04:10:51', 'capture_1_20250608_111042_annotated.jpg', 'uploads/capture_1_20250608_111042_annotated.jpg', 'oli_palsu', 31.12, 'Oli yang diidentifikasi sebagai \'oli_palsu\' menunjukkan perbedaan warna yang signifikan dibandingkan oli asli.  Warna oli palsu terlihat lebih gelap, bahkan cenderung hitam pekat, yang mengindikasikan kemungkinan kontaminasi atau kualitas bahan dasar yang buruk.  Hal ini dapat menyebabkan penurunan performa mesin dan kerusakan komponen internal.\n\nKondisi oli palsu tersebut sangat tidak layak untuk digunakan pada sepeda motor.  Penggunaan oli palsu dapat mengakibatkan keausan mesin yang lebih cepat, peningkatan suhu operasi, dan bahkan kerusakan fatal pada mesin.  Segera lakukan penggantian oli dengan oli yang direkomendasikan pabrikan sepeda motor Anda.\n\nRekomendasi perawatan adalah segera mengganti oli palsu dengan oli yang sesuai spesifikasi dan berkualitas.  Lakukan juga pengecekan kondisi mesin dan filter oli.  Hindari penggunaan oli palsu di masa mendatang untuk menjaga performa dan umur pakai mesin sepeda motor Anda. Gunakan hanya oli dari sumber terpercaya dan pastikan sesuai dengan spesifikasi yang direkomendasikan oleh pabrikan motor.\n'),
(121, 1, '2025-06-08 05:10:45', 'capture_1_20250608_121035_annotated.jpg', 'uploads/capture_1_20250608_121035_annotated.jpg', 'oli_asli', 76.98, 'Oli pada gambar tampak berwarna cokelat keemasan, menunjukkan kemungkinan oli telah digunakan dalam jangka waktu tertentu. Warna ini mengindikasikan adanya kontaminan dan kemungkinan penurunan viskositas.  Meskipun terlihat masih cukup jernih,  perlu pemeriksaan lebih lanjut untuk memastikan kondisi sebenarnya, misalnya dengan uji viskositas.\n\nRekomendasi perawatan adalah segera melakukan penggantian oli.  Gunakan oli baru yang sesuai dengan spesifikasi pabrikan sepeda motor.  Frekuensi penggantian oli sebaiknya sesuai dengan buku panduan perawatan kendaraan atau saran dari mekanik handal.  Jangan menunda penggantian jika oli sudah menunjukkan tanda-tanda perubahan warna signifikan.\n\nUntuk menjaga performa mesin, pastikan selalu menggunakan oli yang direkomendasikan pabrikan.  Lakukan pengecekan rutin terhadap tingkat oli dan perhatikan perubahan warna atau konsistensi.  Penggantian oli secara berkala sangat penting untuk mencegah kerusakan mesin akibat gesekan antar komponen dan pembentukan endapan.\n'),
(122, 1, '2025-06-08 05:11:59', 'capture_1_20250608_121159_annotated.jpg', 'uploads/capture_1_20250608_121159_annotated.jpg', 'Tidak Terdeteksi', 0, 'Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan.'),
(123, 1, '2025-06-08 05:12:46', 'capture_1_20250608_121237_annotated.jpg', 'uploads/capture_1_20250608_121237_annotated.jpg', 'oli_asli', 57.02, 'Oli pada gambar menunjukkan warna coklat keemasan yang agak gelap, mengindikasikan oli telah digunakan dan mungkin sudah mendekati masa penggantian.  Tingkat kekotoran tidak terlihat secara signifikan dari gambar, namun warna gelapnya mengindikasikan adanya kemungkinan degradasi kualitas oli akibat pemakaian dan oksidasi.  Penggantian oli segera direkomendasikan untuk menjaga performa mesin.\n\nUntuk perawatan, ganti oli sesuai rekomendasi pabrikan sepeda motor,  biasanya setiap 2000-4000 km atau 3-6 bulan tergantung pemakaian.  Periksa secara berkala kondisi oli melalui dipstick,  dan perhatikan perubahan warna atau bau yang tidak wajar.  Gunakan filter oli baru setiap kali penggantian oli.\n\nSelain penggantian rutin, pastikan selalu menggunakan oli yang sesuai spesifikasi mesin sepeda motor.  Hindari penggunaan oli yang telah melebihi masa pakai atau terkontaminasi.  Dengan perawatan yang tepat,  oli yang berkualitas akan membantu menjaga performa mesin dan memperpanjang usia pakainya.\n'),
(127, 1, '2025-06-09 04:48:32', 'capture_1_20250609_114820_annotated.jpg', 'uploads/capture_1_20250609_114820_annotated.jpg', 'person', 0, 'Gambar tersebut menunjukkan seorang pria yang sedang membuat tanda \'damai\' atau \'V\' dengan tangannya.  Latar belakangnya buram, tetapi tampak seperti interior ruangan yang redup. Kualitas gambar agak buram dan berbutir, mungkin karena kualitas foto yang kurang baik atau efek filter.  Tidak ada objek lain yang signifikan terlihat di gambar ini.\n\nKarena gambar hanya menampilkan seorang pria dan tidak ada hubungannya dengan sepeda motor atau oli, maka analisis kondisi oli tidak relevan.  Pria tersebut sepertinya sedang berfoto selfie, dan tanda \'V\' mungkin menunjukkan sikap ramah, senang, atau sebagai bentuk salam.  Dia terlihat santai dan tidak ada indikasi kegiatan atau situasi khusus lainnya.\n\nSecara keseluruhan, gambar ini adalah potret sederhana dari seorang pria yang sedang berpose di depan kamera.  Keburaman gambar sedikit mengaburkan detail, tetapi ekspresi wajahnya tampak netral dan santai.  Tidak ada elemen tambahan yang dapat memberikan konteks lebih lanjut.\n'),
(129, 1, '2025-06-09 07:39:41', 'capture_1_20250609_143927_annotated.jpg', 'uploads/capture_1_20250609_143927_annotated.jpg', 'oli_asli, person', 0, 'Gambar tersebut menampilkan seorang pria muda yang sedang membuat tanda \"damai\" (peace sign) dengan tangannya.  Ia berada di dalam ruangan yang tampak seperti gudang atau ruang penyimpanan, dengan rak-rak berisi botol dan benda-benda lainnya di latar belakang.  Kualitas gambar sedikit buram dan memiliki filter warna ungu.\n\nJika \"oli_asli\" mengacu pada pria dalam gambar, ia tampak santai dan mungkin sedang mengambil foto selfie atau video singkat.  Tidak ada informasi lebih lanjut yang bisa disimpulkan dari gambar mengenai aktivitas atau situasinya.  Identifikasi \'oli_asli\' dalam konteks ini tampaknya keliru.\n\nDengan mempertimbangkan kualitas gambar yang buram dan informasi yang terbatas, tidak mungkin untuk menentukan dengan pasti objek \"oli_asli\" jika bukan merujuk kepada pria tersebut.  Identifikasi tersebut mungkin kesalahan dari model deteksi objek.  Perlu lebih banyak informasi atau gambar yang lebih jelas untuk memberikan analisis yang lebih akurat.\n'),
(130, 1, '2025-06-10 01:45:25', 'capture_1_20250610_084508_annotated.jpg', 'uploads/capture_1_20250610_084508_annotated.jpg', 'person', 0, 'Gambar tersebut menampilkan bagian atas tubuh seorang pria dengan rambut gelap.  Latar belakangnya menunjukkan interior ruangan sederhana dengan dinding berwarna biru pucat, pintu berwarna putih, dan beberapa kotak atau lubang di dinding. Kualitas gambarnya agak buram, dan detailnya sulit diidentifikasi secara pasti.\n\nKarena tidak ada informasi yang menunjukkan hubungan antara pria tersebut dengan sepeda motor atau oli, maka kita tidak bisa menganalisis kualitas oli atau merek/warna sepeda motor.  Tampaknya pria tersebut sedang berada di dalam rumahnya dan kemungkinan sedang merekam video atau mengambil foto selfie.  Posisi dan ekspresi wajahnya tidak memberikan informasi lebih lanjut tentang aktivitasnya.\n\nSecara keseluruhan, gambar ini adalah foto yang diambil dari sudut pandang yang tidak biasa, dan fokus utamanya adalah wajah pria tersebut. Tidak ada objek lain yang signifikan atau informasi kontekstual yang jelas dalam gambar. Kualitas gambar yang kurang tajam menyulitkan untuk memberikan analisis lebih rinci.\n'),
(131, 1, '2025-06-10 01:48:42', 'capture_1_20250610_084832_annotated.jpg', 'uploads/capture_1_20250610_084832_annotated.jpg', 'Honda_Beat_Hijau', 0, 'Gambar tersebut menunjukkan sebuah sepeda motor matic berwarna gelap, yang diidentifikasi sebagai Honda Beat Hijau oleh model deteksi objek.  Kendaraan tersebut terparkir di area yang tampak seperti garasi rumah atau carport yang sederhana.  Di latar belakang terlihat sebuah sepeda juga terparkir. Kondisi pencahayaan pada gambar kurang terang.\n\nMeskipun identifikasi model deteksi objek menyebutkan \"Hijau,\" sepeda motor pada gambar terlihat berwarna gelap, mungkin hitam atau abu-abu gelap.  Identifikasi warna tampaknya keliru.  Model Honda Beat yang tepat sulit dipastikan dari gambar ini, tetapi bentuk dan detailnya konsisten dengan desain umum motor Honda Beat.  Tidak ada informasi yang terlihat terkait oli mesin sepeda motor tersebut.\n\nKesimpulannya, gambar menunjukkan sebuah sepeda motor Honda Beat dengan warna yang berbeda dari yang diidentifikasi oleh model.  Kualitas gambar yang kurang baik dan kurangnya detail tambahan menghambat analisis lebih lanjut, misalnya mengenai kondisi oli atau aktivitas yang berkaitan dengan motor tersebut.\n'),
(132, 1, '2025-06-10 06:55:20', 'capture_1_20250610_135510_annotated.jpg', 'uploads/capture_1_20250610_135510_annotated.jpg', 'Honda_Beat_Hitam, person', 0, 'Gambar tersebut menampilkan sebuah skuter matik berwarna gelap yang terparkir di area yang tampak seperti halaman rumah atau tempat parkir sederhana.  Terlihat juga sebuah becak dan sepotong laptop di latar depan gambar.  Konteks gambar menunjukkan skuter tersebut mungkin milik seseorang yang tinggal di area tersebut atau sedang berkunjung. Tidak ada indikasi kondisi oli atau merek/warna skuter yang terlihat secara jelas.\n\nGambar ini tidak memberikan informasi mengenai kondisi oli atau merek sepeda motor.  Oleh karena itu, tidak memungkinkan untuk memberikan analisis kualitas oli atau saran perawatan.  \'Person\' dalam konteks ini merujuk pada pemilik atau pengguna skuter tersebut yang tidak terlihat dalam gambar.\n\nKemungkinan besar, gambar diambil secara acak, menampilkan skuter yang terparkir.  Tidak ada aktivitas manusia yang terlihat secara langsung dalam gambar, dan fokus utamanya adalah pada skuter itu sendiri.  Identifikasi \'person\' sebagai subjek utama mungkin kurang tepat, karena lebih tepat untuk menyebut objek utama sebagai \'skuter matik\'.  Merek dan model skuter tidak dapat diidentifikasi dengan pasti dari gambar ini.\n'),
(133, 1, '2025-06-10 07:04:50', 'capture_1_20250610_140438_annotated.jpg', 'uploads/capture_1_20250610_140438_annotated.jpg', 'Yamaha_Aerox_Hitam, merk_oli, person', 0, 'Gambar tersebut menunjukkan dua sepeda motor yang diparkir di pinggir jalan di depan sebuah warung. Sepeda motor yang lebih dekat ke kamera berwarna hitam, sedangkan yang satunya lagi berwarna merah.  Terlihat juga sebuah becak di sebelah kiri, dan beberapa sepeda motor lain yang diparkir lebih jauh di latar belakang. Konteksnya kemungkinan merupakan area parkir di dekat tempat usaha kecil.\n\n\nMengingat \'merk_oli\' dalam konteks ini kemungkinan merujuk pada jenis atau merk oli yang digunakan oleh sepeda motor tersebut,  tidak mungkin untuk menganalisis kualitas oli berdasarkan gambar.  Tidak ada informasi yang terlihat terkait merek oli atau kondisi oli tersebut.  Untuk mengetahui kualitas dan kebutuhan perawatan/penggantian oli, diperlukan inspeksi langsung pada oli dan/atau konsultasi mekanik.\n\n\nJika \'merk_oli\' salah interpretasi dan bukan mengacu pada oli, maka bisa jadi merupakan deskripsi yang salah.  Gambar tidak memberikan informasi tentang merek atau warna spesifik sepeda motor tersebut selain warna merah dan hitam.  Kemungkinan model sepeda motor juga tidak bisa ditentukan dengan pasti karena detailnya tidak cukup jelas di gambar.\n'),
(134, 1, '2025-06-10 07:13:17', 'capture_1_20250610_141303_annotated.jpg', 'uploads/capture_1_20250610_141303_annotated.jpg', 'person', 0, 'Gambar tersebut menampilkan sebuah jalan di depan beberapa toko atau warung kecil di Indonesia.  Seorang pria berpakaian hijau muda dan helm biru terlihat berdiri di dekat sebuah sepeda motor matic berwarna biru gelap.  Terlihat juga beberapa sepeda motor lain yang terparkir di latar belakang, serta sebuah warung bakso yang bertuliskan \"Bakso Sarap\" pada papan namanya. Kondisi lingkungan tampak sederhana dan ramai.\n\nPria tersebut kemungkinan sedang menunggu atau beristirahat dekat sepeda motornya.  Tidak ada informasi yang terlihat terkait kondisi oli sepeda motor atau merek/warna spesifik sepeda motornya.  Berdasarkan posisinya, ia mungkin pemilik atau pengguna sepeda motor tersebut.\n\nTidak ada indikasi dari gambar yang menunjukkan hubungan pria tersebut dengan kualitas oli atau merek/warna sepeda motor.  Analisis mengenai kualitas oli dan perawatan motor tidak dapat dilakukan berdasarkan gambar yang tersedia.\n');

-- --------------------------------------------------------

--
-- Table structure for table `deteksi`
--

CREATE TABLE `deteksi` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `timestamp` datetime DEFAULT NULL,
  `image_name` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `detection_class` varchar(100) DEFAULT NULL,
  `confidence_score` float DEFAULT NULL,
  `generative_description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

CREATE TABLE `user` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `created_at`) VALUES
(1, 'razagopo', 'raza.gopo@gmail.com', 'scrypt:32768:8:1$Qlh7O26e7IUwYpNG$f85a1c0a12d2cb7a1b89bfe666578e07b32a53ecddaff71987e4ad9c20ab1d9e19162a15f5089af5002767c88d2372f620e353efadf7535b1e87f0d2d6ced420', '2025-06-02 13:49:49'),
(2, 'nailar', 'nailarraza16@gmail.com', 'scrypt:32768:8:1$MIyoAosJ2Me2Pukg$d691274d4a6a385f192e43b34205a5afffe4656dfc28992f5bddcfd5388825988ffc5da1824d7c7398951d03a11ca31fd1465808dee7768534b9a799883752af', '2025-06-03 06:59:35');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `alembic_version`
--
ALTER TABLE `alembic_version`
  ADD PRIMARY KEY (`version_num`);

--
-- Indexes for table `detections`
--
ALTER TABLE `detections`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_user_id` (`user_id`),
  ADD KEY `idx_timestamp` (`timestamp`);

--
-- Indexes for table `deteksi`
--
ALTER TABLE `deteksi`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `ix_Deteksi_timestamp` (`timestamp`);

--
-- Indexes for table `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `detections`
--
ALTER TABLE `detections`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=135;

--
-- AUTO_INCREMENT for table `deteksi`
--
ALTER TABLE `deteksi`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user`
--
ALTER TABLE `user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `detections`
--
ALTER TABLE `detections`
  ADD CONSTRAINT `detections_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `deteksi`
--
ALTER TABLE `deteksi`
  ADD CONSTRAINT `deteksi_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
